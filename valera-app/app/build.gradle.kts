plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    // 1. Возвращаем плагин для Compose (обязателен для Kotlin 2.0)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "com.hmuriy.valera"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.hmuriy.valera"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildFeatures {
        compose = true
    }

    // 2. Явно задаем совместимость с Java 1.8 для обоих компиляторов
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }

    kotlinOptions {
        jvmTarget = "1.8"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
    implementation("androidx.activity:activity-compose:1.8.2")

    // --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
    // Используем версию из libs (2024.09.00), чтобы она совпадала с тестами
    implementation(platform(libs.androidx.compose.bom))

    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")

    implementation("androidx.lifecycle:lifecycle-service:2.7.0")
    implementation("androidx.datastore:datastore-preferences:1.0.0")
    implementation("androidx.savedstate:savedstate-ktx:1.2.1")

    // Тесты
    testImplementation(libs.junit)

    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)

    // Тесты Compose (версия также берется из libs)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)

    debugImplementation(libs.androidx.compose.ui.test.manifest)
    // Опционально: tooling для превью
    debugImplementation(libs.androidx.compose.ui.tooling)
}