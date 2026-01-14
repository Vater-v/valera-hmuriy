package com.hmuriy.valera.ui.overlay

import androidx.compose.animation.*
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.FastOutLinearInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.hmuriy.valera.core.theme.*
import com.hmuriy.valera.domain.OverlayState

// --- 1. КНОПКА МЕНЮ (V) ---
@Composable
fun VWidget() {
    val isOpen by OverlayState.isMenuOpen
    val isAuto by OverlayState.isAutomation

    Box(contentAlignment = Alignment.Center) {
        if (!isOpen) {
            // КНОПКА ОТКРЫТИЯ
            // Анимацию появления самой кнопки тоже можно сделать приятной
            AnimatedVisibility(
                visible = true,
                enter = scaleIn(animationSpec = spring(dampingRatio = Spring.DampingRatioMediumBouncy)) + fadeIn()
            ) {
                Box(
                    modifier = Modifier
                        .size(42.dp)
                        .windowDraggable()
                        .background(BlackBg.copy(alpha = 0.9f), CircleShape)
                        .border(1.dp, RedPrimary.copy(alpha = 0.7f), CircleShape)
                        .clickable { OverlayState.isMenuOpen.value = true },
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "V",
                        color = TextWhite,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        } else {
            // МЕНЮ
            // Добавляем анимацию открытия меню (разворачивание)
            AnimatedVisibility(
                visible = true,
                enter = scaleIn(
                    initialScale = 0.9f,
                    animationSpec = spring(
                        dampingRatio = Spring.DampingRatioLowBouncy,
                        stiffness = Spring.StiffnessMedium
                    )
                ) + fadeIn(tween(150)),
                exit = scaleOut(targetScale = 0.9f, animationSpec = tween(100)) + fadeOut(tween(100))
            ) {
                Box(
                    modifier = Modifier
                        .width(220.dp)
                        .windowDraggable()
                        .background(Color(0xFF0F0F0F), RoundedCornerShape(4.dp))
                        .border(1.dp, Color(0xFF333333), RoundedCornerShape(4.dp))
                ) {
                    Column(Modifier.padding(vertical = 12.dp, horizontal = 16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "VALERA",
                                color = Color(0xFF888888),
                                fontSize = 12.sp,
                                letterSpacing = 2.sp,
                                fontWeight = FontWeight.Medium
                            )
                            Icon(
                                imageVector = Icons.Default.Close,
                                contentDescription = "Close",
                                tint = RedPrimary,
                                modifier = Modifier
                                    .size(18.dp)
                                    .clickable { OverlayState.isMenuOpen.value = false }
                            )
                        }

                        Spacer(Modifier.height(16.dp))

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Automation",
                                color = TextWhite,
                                fontSize = 14.sp
                            )

                            Switch(
                                checked = isAuto,
                                onCheckedChange = { OverlayState.isAutomation.value = it },
                                modifier = Modifier.scale(0.7f).height(24.dp),
                                colors = SwitchDefaults.colors(
                                    checkedThumbColor = RedPrimary,
                                    checkedTrackColor = Color(0xFF333333),
                                    uncheckedThumbColor = Color(0xFF888888),
                                    uncheckedTrackColor = Color(0xFF1A1A1A),
                                    checkedBorderColor = Color.Transparent,
                                    uncheckedBorderColor = Color.Transparent
                                )
                            )
                        }
                    }
                }
            }
        }
    }
}

// --- 2. TOAST (Уведомление снизу) ---
@Composable
fun ToastWidget() {
    val message by OverlayState.currentToast

    AnimatedVisibility(
        visible = message != null,
        // MODERN POP-IN ANIMATION
        // Эффект "выпрыгивания" с пружиной
        enter = scaleIn(
            initialScale = 0.6f, // Начинаем с 60% размера
            animationSpec = spring(
                dampingRatio = 0.65f, // Коэффициент упругости (меньше 1.0 = прыгает)
                stiffness = Spring.StiffnessMedium
            )
        ) + fadeIn(tween(150)), // Быстрое появление прозрачности

        // Быстрый уход (Scale Out + Fade Out)
        exit = scaleOut(
            targetScale = 0.8f,
            animationSpec = tween(150, easing = FastOutLinearInEasing)
        ) + fadeOut(tween(100))
    ) {
        Box(
            modifier = Modifier
                .windowDraggable()
                .padding(bottom = 32.dp)
                .background(Color(0xFF111111), RoundedCornerShape(4.dp))
                .border(1.dp, Color(0xFF333333), RoundedCornerShape(4.dp))
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(end = 16.dp)
            ) {
                Box(
                    modifier = Modifier
                        .width(4.dp)
                        .height(36.dp)
                        .background(RedPrimary)
                )

                Spacer(modifier = Modifier.width(12.dp))

                Text(
                    text = message ?: "",
                    color = Color(0xFFEEEEEE),
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    lineHeight = 20.sp
                )
            }
        }
    }
}

// --- 3. HINT (Подсказка сверху) ---
@Composable
fun HintWidget() {
    val message by OverlayState.currentHint

    AnimatedVisibility(
        visible = message != null,
        // Тоже пружинный эффект, но чуть мягче для верхнего уведомления
        enter = slideInVertically(
            initialOffsetY = { -it }, // Выезжает сверху
            animationSpec = spring(
                dampingRatio = 0.7f,
                stiffness = Spring.StiffnessMediumLow
            )
        ) + fadeIn(tween(100)),

        // Уезжает вверх при скрытии
        exit = slideOutVertically(
            targetOffsetY = { -it },
            animationSpec = tween(200)
        ) + fadeOut(tween(200))
    ) {
        Box(
            modifier = Modifier
                .windowDraggable()
                .padding(top = 24.dp)
                .background(Color(0xFF151515), RoundedCornerShape(8.dp)) // Чуть больше скругление для "капсулы"
                .border(0.5.dp, Color(0xFF444444), RoundedCornerShape(8.dp))
                .padding(horizontal = 16.dp, vertical = 8.dp)
        ) {
            Text(
                text = message ?: "",
                color = Color.White,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold, // Чуть жирнее для читаемости
                letterSpacing = 0.5.sp,
                textAlign = TextAlign.Center
            )
        }
    }
}