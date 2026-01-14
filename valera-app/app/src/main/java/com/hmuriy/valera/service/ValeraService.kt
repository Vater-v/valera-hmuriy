package com.hmuriy.valera.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.hmuriy.valera.R
import com.hmuriy.valera.data.SettingsRepo
import com.hmuriy.valera.domain.TcpClient
import com.hmuriy.valera.domain.OverlayState
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.distinctUntilChanged

class ValeraService : Service() {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var overlayManager: OverlayManager? = null
    private var tcpClient: TcpClient? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        startForegroundNotif()
        overlayManager = OverlayManager(this)
        overlayManager?.create()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Запускаем наблюдатель за настройками
        scope.launch {
            SettingsRepo(applicationContext).ipFlow
                .distinctUntilChanged() // Реагируем только если IP реально изменился
                .collectLatest { savedIp ->
                    Log.d("Valera", "Settings IP changed to: $savedIp")

                    // Останавливаем старый клиент перед созданием нового
                    tcpClient?.stop()
                    tcpClient = null

                    val parts = savedIp.split(":")
                    if (parts.size == 2) {
                        val ip = parts[0]
                        val port = parts[1].toIntOrNull()

                        if (port != null) {
                            Log.d("Valera", "Starting TcpClient on $ip:$port")
                            tcpClient = TcpClient(ip, port)
                            tcpClient?.start()
                        } else {
                            Log.e("Valera", "Invalid port in settings: $savedIp")
                        }
                    } else {
                        Log.e("Valera", "Invalid IP format in settings: $savedIp")
                    }
                }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        overlayManager?.destroy()
        tcpClient?.stop()
        scope.cancel()
        super.onDestroy()
    }

    private fun startForegroundNotif() {
        val chanId = "valera_service"
        val manager = getSystemService(NotificationManager::class.java)
        val channel = NotificationChannel(chanId, "Valera Overlay", NotificationManager.IMPORTANCE_LOW)
        manager.createNotificationChannel(channel)

        val notif = NotificationCompat.Builder(this, chanId)
            .setContentTitle("Valera Hmuriy")
            .setContentText("Bridge Active: 11111 -> Target")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setOngoing(true)
            .build()

        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(1, notif, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(1, notif)
        }
    }
}