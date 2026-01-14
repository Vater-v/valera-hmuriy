package com.hmuriy.valera.service

import android.content.Context
import android.graphics.PixelFormat
import android.os.Build
import android.os.Bundle
import android.view.ContextThemeWrapper // Важный импорт
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import androidx.compose.ui.platform.ComposeView
import androidx.lifecycle.*
import androidx.savedstate.*
import com.hmuriy.valera.R // Импорт R для доступа к стилям
import com.hmuriy.valera.core.theme.ValeraTheme
import com.hmuriy.valera.ui.overlay.*

class OverlayManager(private val context: Context) {
    private val wm = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager

    // Храним ссылки для очистки
    private val views = mutableListOf<View>()
    private val lifecycleOwners = mutableMapOf<View, MyLifecycleOwner>()

    private var vView: View? = null
    private var toastView: View? = null
    private var hintView: View? = null

    fun create() {
        // 1. V-Button (Слева)
        vView = createView { VWidget() }.also {
            addToWindow(it, createParams(Gravity.START or Gravity.CENTER_VERTICAL, 0, 0))
        }

        // 2. Toast (Снизу)
        toastView = createView { ToastWidget() }.also {
            addToWindow(it, createParams(Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL, 0, 150))
        }

        // 3. Hint (Сверху)
        hintView = createView { HintWidget() }.also {
            addToWindow(it, createParams(Gravity.TOP or Gravity.CENTER_HORIZONTAL, 0, 150))
        }
    }

    fun destroy() {
        val viewsToRemove = ArrayList(views)
        viewsToRemove.forEach { removeView(it) }
        views.clear()
        vView = null
        toastView = null
        hintView = null
    }

    private fun addToWindow(view: View, params: WindowManager.LayoutParams) {
        try {
            wm.addView(view, params)
            views.add(view)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun removeView(view: View) {
        try {
            wm.removeView(view)
            lifecycleOwners[view]?.handleLifecycleEvent(Lifecycle.Event.ON_DESTROY)
            lifecycleOwners.remove(view)
        } catch (e: Exception) {
            // View уже удалена
        }
    }

    private fun createParams(grav: Int, x: Int, y: Int): WindowManager.LayoutParams {
        val type = if (Build.VERSION.SDK_INT >= 26)
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        else WindowManager.LayoutParams.TYPE_PHONE

        return WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            type,
            // FLAG_NOT_FOCUSABLE пропускает клики мимо кнопок в игру,
            // но из-за него кнопка "Назад" не будет работать в меню.
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                    WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = grav
            this.x = x
            this.y = y
        }
    }

    private fun createView(content: @androidx.compose.runtime.Composable () -> Unit): View {
        // !!! КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ !!!
        // Оборачиваем контекст в тему приложения. Без этого крашится при клике (Ripple effect).
        val themedContext = ContextThemeWrapper(context, R.style.Theme_Valera)

        return ComposeView(themedContext).apply {
            val owner = MyLifecycleOwner()
            // Запускаем жизненный цикл, чтобы работали анимации
            owner.performRestore(null)
            owner.handleLifecycleEvent(Lifecycle.Event.ON_CREATE)
            owner.handleLifecycleEvent(Lifecycle.Event.ON_START)
            owner.handleLifecycleEvent(Lifecycle.Event.ON_RESUME)

            setViewTreeLifecycleOwner(owner)
            setViewTreeSavedStateRegistryOwner(owner)
            setContent { ValeraTheme { content() } }

            lifecycleOwners[this] = owner
        }
    }

    // Lifecycle Owner для Compose
    class MyLifecycleOwner : SavedStateRegistryOwner {
        private val lifecycleRegistry = LifecycleRegistry(this)
        private val controller = SavedStateRegistryController.create(this)
        override val lifecycle: Lifecycle get() = lifecycleRegistry
        override val savedStateRegistry: SavedStateRegistry get() = controller.savedStateRegistry
        fun handleLifecycleEvent(e: Lifecycle.Event) = lifecycleRegistry.handleLifecycleEvent(e)
        fun performRestore(s: Bundle?) = controller.performRestore(s)
    }
}