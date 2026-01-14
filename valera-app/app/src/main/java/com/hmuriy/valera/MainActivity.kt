package com.hmuriy.valera

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.hmuriy.valera.core.theme.*
import com.hmuriy.valera.data.SettingsRepo
import com.hmuriy.valera.service.ValeraService
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ValeraTheme { MainScreen() }
        }
    }
}

@Composable
fun MainScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val settings = remember { SettingsRepo(context) }
    var ipText by remember { mutableStateOf("") }
    var isRunning by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        settings.ipFlow.collect { ipText = it }
    }

    Column(
        Modifier.fillMaxSize().background(BlackBg).padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Row(Modifier.fillMaxWidth().height(40.dp).background(Surface),
            horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
            Text("ADMIN PANEL", color = TextGray, fontSize = 12.sp)
        }

        Spacer(Modifier.height(60.dp))
        Text("VALERA HMURIY", color = TextWhite, fontSize = 24.sp, fontWeight = FontWeight.Bold, letterSpacing = 4.sp)
        Spacer(Modifier.height(40.dp))

        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            if (ipText.isEmpty()) Text("IP:PORT", color = Color.Gray)
            BasicTextField(
                value = ipText,
                onValueChange = { ipText = it },
                textStyle = TextStyle(color = TextWhite, fontSize = 18.sp, textAlign = TextAlign.Center),
                cursorBrush = SolidColor(RedPrimary),
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )
            Divider(Modifier.align(Alignment.BottomCenter), color = RedPrimary)
        }

        Spacer(Modifier.height(40.dp))

        Button(
            onClick = {
                if (!Settings.canDrawOverlays(context)) {
                    context.startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:${context.packageName}")))
                    return@Button
                }
                scope.launch { settings.saveIp(ipText) }
                val intent = Intent(context, ValeraService::class.java)
                if (isRunning) {
                    context.stopService(intent)
                    isRunning = false
                } else {
                    if (android.os.Build.VERSION.SDK_INT >= 26) context.startForegroundService(intent)
                    else context.startService(intent)
                    isRunning = true
                }
            },
            colors = ButtonDefaults.buttonColors(containerColor = if(isRunning) RedDark else TextWhite),
            modifier = Modifier.fillMaxWidth().height(50.dp),
            shape = MaterialTheme.shapes.extraSmall
        ) {
            Text(if(isRunning) "STOP" else "START", color = if(isRunning) TextWhite else Color.Black, fontWeight = FontWeight.Bold)
        }
    }
}