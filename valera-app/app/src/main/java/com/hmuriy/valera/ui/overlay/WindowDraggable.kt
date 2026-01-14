package com.hmuriy.valera.ui.overlay

import android.view.Gravity
import android.view.WindowManager
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalView
import kotlin.math.roundToInt

fun Modifier.windowDraggable() = composed {
    val composeView = LocalView.current
    val windowManager = remember { composeView.context.getSystemService(WindowManager::class.java) }

    this.pointerInput(Unit) {
        detectDragGestures { change, dragAmount ->
            change.consume()

            val windowView = composeView.rootView

            if (windowView.windowToken != null && windowView.parent != null) {
                try {
                    val params = windowView.layoutParams as WindowManager.LayoutParams

                    // Определяем текущие настройки Gravity
                    val hGravity = params.gravity and Gravity.HORIZONTAL_GRAVITY_MASK
                    val vGravity = params.gravity and Gravity.VERTICAL_GRAVITY_MASK

                    // 1. Размеры
                    val metrics = windowView.context.resources.displayMetrics
                    val screenWidth = metrics.widthPixels
                    val screenHeight = metrics.heightPixels
                    val viewWidth = windowView.width
                    val viewHeight = windowView.height

                    // 2. Вычисляем смещение с учетом инверсии для BOTTOM и RIGHT/END
                    // Если привязано к правому краю, движение вправо (drag > 0) должно уменьшать отступ X.
                    val isRight = hGravity == Gravity.RIGHT || hGravity == Gravity.END
                    val dx = if (isRight) -dragAmount.x else dragAmount.x

                    // Если привязано к низу, движение вниз (drag > 0) должно уменьшать отступ Y.
                    val isBottom = vGravity == Gravity.BOTTOM
                    val dy = if (isBottom) -dragAmount.y else dragAmount.y

                    var newX = params.x + dx.roundToInt()
                    var newY = params.y + dy.roundToInt()

                    // 3. Ограничение границ (Логика остается той же: координаты всегда >= 0)

                    // X: Обработка
                    if (hGravity == Gravity.CENTER_HORIZONTAL) {
                        val limitX = (screenWidth - viewWidth) / 2
                        newX = newX.coerceIn(-limitX, limitX)
                    } else {
                        // Для LEFT: 0..max, Для RIGHT: 0..max (0 - это край экрана)
                        newX = newX.coerceIn(0, screenWidth - viewWidth)
                    }

                    // Y: Обработка
                    if (vGravity == Gravity.CENTER_VERTICAL) {
                        val limitY = (screenHeight - viewHeight) / 2
                        newY = newY.coerceIn(-limitY, limitY)
                    } else {
                        // Для TOP: 0..max, Для BOTTOM: 0..max
                        newY = newY.coerceIn(0, screenHeight - viewHeight)
                    }

                    // 4. Применяем
                    params.x = newX
                    params.y = newY
                    windowManager.updateViewLayout(windowView, params)

                } catch (e: Exception) {
                    e.printStackTrace()
                }
            }
        }
    }
}