package com.hmuriy.valera.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore("valera_cfg")

class SettingsRepo(private val context: Context) {
    companion object {
        val IP_KEY = stringPreferencesKey("target_ip")
    }
    val ipFlow = context.dataStore.data.map { it[IP_KEY] ?: "" }

    suspend fun saveIp(ip: String) = context.dataStore.edit { it[IP_KEY] = ip }
}