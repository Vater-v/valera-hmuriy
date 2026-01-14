package com.hmuriy.valera.core.theme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val DarkScheme = darkColorScheme(
    primary = RedPrimary,
    background = BlackBg,
    surface = Surface,
    onPrimary = TextWhite,
    onSurface = TextWhite
)

@Composable
fun ValeraTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = DarkScheme, content = content)
}