package com.hmuriy.valera.domain

import androidx.compose.runtime.mutableStateOf
import kotlinx.coroutines.*

object OverlayState {
    // --- UI STATES ---
    val isMenuOpen = mutableStateOf(false)

    // По умолчанию тумблер ВКЛЮЧЕН (true)
    val isAutomation = mutableStateOf(true)

    // --- NOTIFICATIONS ---
    val currentToast = mutableStateOf<String?>(null)
    val currentHint = mutableStateOf<String?>(null)

    // Вспомогательные джобы для авто-скрытия уведомлений
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var toastJob: Job? = null
    private var hintJob: Job? = null

    fun showToast(msg: String) {
        toastJob?.cancel()
        currentToast.value = msg
        toastJob = scope.launch {
            delay(3000) // 3 секунды показываем
            currentToast.value = null
        }
    }

    fun showHint(msg: String) {
        hintJob?.cancel()
        currentHint.value = msg
        hintJob = scope.launch {
            delay(5000) // 5 секунд показываем
            currentHint.value = null
        }
    }
}