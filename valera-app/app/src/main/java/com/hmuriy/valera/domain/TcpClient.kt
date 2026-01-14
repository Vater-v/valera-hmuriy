package com.hmuriy.valera.domain

import android.util.Log
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.channels.Channel
import java.io.PrintWriter
import java.net.ServerSocket
import java.net.Socket
import kotlin.math.min

class TcpClient(private val targetIp: String, private val targetPort: Int) {
    private var serverSocket: ServerSocket? = null

    // SupervisorJob: ошибка в одной корутине не убивает остальные (важно для стабильности)
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    @Volatile
    private var isRunning = true

    // ОПТИМИЗАЦИЯ 1: Очередь с лимитом.
    // Если сервер недоступен, мы храним последние 100 сообщений.
    // Старые удаляются (DROP_OLDEST), чтобы не забить память телефона мусором.
    private val msgQueue = Channel<String>(
        capacity = 100,
        onBufferOverflow = BufferOverflow.DROP_OLDEST
    )

    // Writer для отправки команд в Игру (C++)
    @Volatile
    private var gameWriter: PrintWriter? = null

    fun start() {
        Log.i("Valera", "Starting Smart Bridge...")

        // 1. Запускаем "Brain Worker" (Связь с сервером Python)
        startBrainWorker()

        // 2. Запускаем "Game Server" (Связь с Игрой C++)
        startGameServer()
    }

    private fun startGameServer() {
        scope.launch {
            try {
                // Открываем порт для игры
                serverSocket = ServerSocket(11111)
                OverlayState.showToast("Bridge Ready: 11111 👻")
                Log.i("Valera", "Bridge ServerSocket started on 11111")

                while (isRunning) {
                    try {
                        // Ждем подключения игры
                        val socket = serverSocket?.accept() ?: break

                        // ОПТИМИЗАЦИЯ 2: Отключаем задержку Нейгла для мгновенной передачи
                        socket.tcpNoDelay = true

                        Log.i("Valera", "Game connected!")
                        handleGameConnection(socket)
                    } catch (e: Exception) {
                        if (isRunning) Log.e("Valera", "Accept error", e)
                    }
                }
            } catch (e: Exception) {
                Log.e("Valera", "ServerSocket Fatal Error", e)
                OverlayState.showToast("Port 11111 Error! ❌")
            }
        }
    }

    private fun startBrainWorker() {
        scope.launch {
            while (isRunning) {
                var pythonSocket: Socket? = null
                try {
                    Log.d("Valera", "Connecting to Brain $targetIp:$targetPort...")

                    pythonSocket = Socket(targetIp, targetPort)
                    // ОПТИМИЗАЦИЯ: Мгновенная отправка пакетов на сервер
                    pythonSocket.tcpNoDelay = true
                    pythonSocket.keepAlive = true // Пытаться держать соединение живым

                    val pythonOut = PrintWriter(pythonSocket.getOutputStream(), true)
                    val pythonIn = pythonSocket.getInputStream().bufferedReader(Charsets.UTF_8)

                    OverlayState.showToast("Brain Connected 🟢")
                    Log.i("Valera", "Brain Connected!")

                    // Корутина чтения ОТ Сервера
                    val readerJob = launch {
                        try {
                            var line: String?
                            while (pythonIn.readLine().also { line = it } != null) {
                                val msg = line?.trim() ?: continue
                                processMessageFromBrain(msg)
                            }
                        } catch (e: Exception) {
                            Log.e("Valera", "Brain Read Error", e)
                        }
                    }

                    // Цикл отправки НА Сервер (из очереди)
                    for (msg in msgQueue) {
                        if (pythonOut.checkError()) throw Exception("Write error")
                        pythonOut.println(msg)
                    }

                    readerJob.cancel()

                } catch (e: Exception) {
                    Log.w("Valera", "Brain connection failed: ${e.message}")
                    // Не спамим тостами каждую секунду, если сервер упал надолго
                    // OverlayState.showToast("Brain Offline 🔴")
                    delay(3000) // Пауза перед реконнектом
                } finally {
                    try { pythonSocket?.close() } catch (_: Exception) {}
                }
            }
        }
    }

    private fun handleGameConnection(gameSocket: Socket) {
        scope.launch {
            try {
                val gameOut = PrintWriter(gameSocket.getOutputStream(), true)
                gameWriter = gameOut // Сохраняем, чтобы сервер мог писать сюда

                val gameIn = gameSocket.getInputStream().bufferedReader(Charsets.UTF_8)

                var line: String?
                while (gameIn.readLine().also { line = it } != null) {
                    val msg = line?.trim() ?: continue
                    processMessageFromGame(msg)
                }
            } catch (e: Exception) {
                Log.e("Valera", "Game connection error", e)
            } finally {
                Log.i("Valera", "Game disconnected")
                gameWriter = null
                try { gameSocket.close() } catch (_: Exception) {}
            }
        }
    }

    // === ЛОГИКА ОБРАБОТКИ СООБЩЕНИЙ ===

    // От Игры -> На Сервер (и в UI)
    private suspend fun processMessageFromGame(msg: String) {
        when {
            msg.startsWith("TOAST:") -> {
                // Игра хочет показать тост пользователю
                val content = msg.removePrefix("TOAST:").trim()
                OverlayState.showToast(content)
                // Дублируем в лог сервера
                msgQueue.send(msg)
            }
            msg.startsWith("HINT:") -> {
                // Игра хочет показать подсказку
                OverlayState.showHint(msg.removePrefix("HINT:").trim())
            }
            else -> {
                // JSON или логи -> Чистим и шлем на сервер
                extractJson(msg)?.let { cleanPayload ->
                    msgQueue.send(cleanPayload)
                }
            }
        }
    }

    // От Сервера -> В Игру (или в UI)
    private fun processMessageFromBrain(msg: String) {
        // ОПТИМИЗАЦИЯ: when работает быстрее цепочки if-else и легче читается
        when {
            msg.startsWith("TOAST:") -> {
                // Сервер прислал сообщение для юзера (например "Сервер перегружен")
                val content = msg.removePrefix("TOAST:").trim()
                OverlayState.showToast(content)
            }
            msg.startsWith("HINT:") -> {
                // Сервер прислал подсказку
                val content = msg.removePrefix("HINT:").trim()
                OverlayState.showHint(content)
            }
            else -> {
                // --- ЛОГИКА АВТОМАТИКИ (TUMBLER) ---
                // Проверяем, является ли сообщение командой принятия игры
                // Ищем ключевые слова, чтобы быть уверенными, что это нужный JSON
                if (msg.contains("API:") &&
                    msg.contains("\"stage\": \"GameInitiation\"") &&
                    msg.contains("\"action\": \"Accept\"")) {

                    // Если тумблер выключен (false) -> БЛОКИРУЕМ
                    if (!OverlayState.isAutomation.value) {
                        Log.d("Valera", "AUTOMATION BLOCKED: $msg")
                        return // Выходим из функции, сообщение не дойдет до gameWriter
                    }
                }

                // Если проверки пройдены или это другое сообщение -> отправляем в игру
                gameWriter?.println(msg)
            }
        }
    }

    // Вспомогательная функция очистки мусора перед JSON
    private fun extractJson(msg: String): String? {
        val idxObj = msg.indexOf("{")
        val idxArr = msg.indexOf("[")

        val start = when {
            idxObj != -1 && idxArr != -1 -> min(idxObj, idxArr)
            idxObj != -1 -> idxObj
            idxArr != -1 -> idxArr
            else -> -1
        }

        return if (start != -1) msg.substring(start) else null
    }

    fun stop() {
        isRunning = false
        msgQueue.close()
        try { serverSocket?.close() } catch (_: Exception) {}
        scope.cancel()
        Log.i("Valera", "TcpClient stopped")
    }
}