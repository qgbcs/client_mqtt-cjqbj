package com.qgb.clientmqtt

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import android.util.Base64
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.compose.foundation.Image
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.clickable
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CameraAlt
import androidx.compose.material.icons.outlined.Folder
import androidx.compose.material.icons.outlined.NetworkWifi
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.twotone.Security
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.Switch
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.snapshotFlow
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.chaquo.python.Python
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.json.JSONObject

private data class RemoteFile(
    val path: String,
    val size: Long,
    val modified: Double
)

private data class FeatureDescriptor(
    val name: String,
    val title: String,
    val actions: List<String>
)

@OptIn(ExperimentalFoundationApi::class, ExperimentalMaterial3Api::class)
class MainActivity : ComponentActivity() {
    private val cameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            cameraPermission.launch(Manifest.permission.CAMERA)
        }
        setContent {
            ClientMqttScreen()
        }
    }
}

@OptIn(ExperimentalFoundationApi::class, ExperimentalMaterial3Api::class)
@Composable
private fun ClientMqttScreen() {
    var features by remember { mutableStateOf(listOf<FeatureDescriptor>()) }
    val pagerState = rememberPagerState(pageCount = { features.size })
    val pagerScope = rememberCoroutineScope()
    var settings by remember { mutableStateOf(false) }
    var permissions by remember { mutableStateOf(false) }
    var selectedDevice by remember { mutableStateOf("Target") }
    var onlineStatus by remember { mutableStateOf("checking") }
    val service = remember { Python.getInstance().getModule("client_service") }

    LaunchedEffect(Unit) {
        while (true) {
            runCatching {
                val raw = withContext(Dispatchers.IO) { service.callAttr("feature_catalog").toString() }
                val array = org.json.JSONArray(raw)
                val updated = buildList {
                    for (index in 0 until array.length()) {
                        val item = array.optJSONObject(index) ?: continue
                        add(FeatureDescriptor(
                            item.optString("name"),
                            item.optString("title", item.optString("name")),
                            buildList {
                                val actions = item.optJSONArray("actions") ?: org.json.JSONArray()
                                for (actionIndex in 0 until actions.length()) add(actions.optString(actionIndex))
                            }
                        ))
                    }
                }
                features = updated
            }
            delay(3_000)
        }
    }

    LaunchedEffect(selectedDevice) {
        while (true) {
            onlineStatus = withContext(Dispatchers.IO) {
                runCatching { JSONObject(service.callAttr("online").toString()).optBoolean("ok") }
                    .getOrDefault(false)
                    .let { if (it) "online" else "offline" }
            }
            delay(30_000)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(selectedDevice)
                        Text(onlineStatus, style = MaterialTheme.typography.labelSmall)
                    }
                },
                actions = {
                    IconButton(onClick = { settings = true }) {
                        Icon(Icons.Outlined.Settings, contentDescription = "Settings")
                    }
                }
            )
        }
    ) { padding ->
        if (permissions) {
            PermissionPage(onBack = { permissions = false })
        } else if (settings) {
            SettingsPage(
                modifier = Modifier.padding(padding),
                onBack = { settings = false },
                onDeviceChanged = { selectedDevice = it },
                onPermissions = { permissions = true }
            )
        } else {
            Column(modifier = Modifier.fillMaxSize().padding(padding)) {
                ScrollableTabRow(selectedTabIndex = pagerState.currentPage) {
                            features.forEachIndexed { index, feature ->
                        Tab(
                            selected = pagerState.currentPage == index,
                            onClick = { pagerScope.launch { pagerState.animateScrollToPage(index) } },
                                    text = { Text(feature.title) },
                            icon = {
                                Icon(
                                    imageVector = when (index) {
                                                else -> when (feature.name) {
                                                    "files" -> Icons.Outlined.Folder
                                                    "camera" -> Icons.Outlined.CameraAlt
                                                    "wifi" -> Icons.Outlined.NetworkWifi
                                                    else -> Icons.Outlined.Settings
                                                }
                                    },
                                            contentDescription = feature.title
                                )
                            }
                        )
                    }
                }
                if (features.isEmpty()) {
                    Text("No feature scripts found", modifier = Modifier.padding(16.dp))
                } else {
                    HorizontalPager(state = pagerState, modifier = Modifier.fillMaxSize()) { page ->
                        when (features[page].name) {
                            "files" -> FilesPage()
                            "camera" -> CameraPage()
                            "wifi" -> WifiPage()
                            else -> DynamicFeaturePage(features[page])
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun FilesPage() {
    var root by remember { mutableStateOf("/data/data") }
    var limit by remember { mutableStateOf("100") }
    var status by remember { mutableStateOf("Ready") }
    var entries by remember { mutableStateOf(listOf<RemoteFile>()) }
    var nextOffset by remember { mutableStateOf(0) }
    var hasMore by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(false) }
    var preview by remember { mutableStateOf<ImageBitmap?>(null) }
    val service = remember { Python.getInstance().getModule("client_service") }
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()

    fun loadPage(start: Int) {
        if (loading) return
        loading = true
        status = "Scanning page at $start..."
        val pageSize = limit.toIntOrNull()?.coerceIn(1, 10000) ?: 100
        scope.launch {
            val raw = withContext(Dispatchers.IO) {
                service.callAttr("call_feature", "files", "scan", root, start, pageSize).toString()
            }
            try {
                val result = JSONObject(raw)
                val page = result.optJSONArray("items") ?: org.json.JSONArray()
                val newEntries = buildList {
                    for (index in 0 until page.length()) {
                        val item = page.optJSONObject(index) ?: continue
                        add(RemoteFile(item.optString("path"), item.optLong("size"), item.optDouble("modified")))
                    }
                }
                entries = if (start == 0) newEntries else entries + newEntries
                hasMore = result.optBoolean("has_more")
                nextOffset = result.optInt("next_offset", start + newEntries.size)
                status = "Loaded ${entries.size} files${if (hasMore) ", more below" else ""}"
            } catch (error: Exception) {
                status = "Invalid scan response: ${error.message}"
            } finally {
                loading = false
            }
        }
    }

    LaunchedEffect(listState, hasMore, loading, entries.size) {
        snapshotFlow { listState.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: -1 }
            .collect { last ->
                if (hasMore && !loading && entries.isNotEmpty() && last >= entries.lastIndex) {
                    loadPage(nextOffset)
                }
            }
    }
    Column(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            OutlinedTextField(root, { root = it }, Modifier.weight(1f), singleLine = true, label = { Text("Remote root") })
            OutlinedTextField(limit, { limit = it.filter(Char::isDigit) }, Modifier.weight(.35f), singleLine = true, label = { Text("Page") })
        }
        Button(onClick = {
            entries = emptyList()
            nextOffset = 0
            hasMore = false
            loadPage(0)
        }) { Text("Scan recursively") }
        Text(status, style = MaterialTheme.typography.labelMedium)
        LazyColumn(state = listState, verticalArrangement = Arrangement.spacedBy(4.dp)) {
            items(entries) { entry ->
                Row(
                    Modifier.fillMaxWidth().clickable {
                        status = "Downloading ${entry.path}..."
                        scope.launch {
                            try {
                                val transfer = withContext(Dispatchers.IO) {
                                    service.callAttr("call_feature", "files", "upload", root.trimEnd('/') + "/" + entry.path).toString()
                                }
                                val transferJson = JSONObject(transfer)
                                val url = transferJson.optString("url")
                                if (url.isBlank()) error(transferJson.optString("error", "upload failed"))
                                withContext(Dispatchers.IO) {
                                    service.callAttr("download_remote_to_file", url, entry.path.substringAfterLast('/')).toString()
                                }
                                if (entry.path.lowercase().matches(Regex(".*\\.(jpg|jpeg|png|webp|gif)$"))) {
                                    val encoded = withContext(Dispatchers.IO) {
                                        service.callAttr("download_transfer_base64", url).toString()
                                    }
                                    val bytes = Base64.decode(encoded, Base64.DEFAULT)
                                    preview = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
                                }
                                status = "Saved to app script directory downloads/"
                            } catch (error: Exception) {
                                status = "Download failed: ${error.message}"
                            }
                        }
                    }.padding(vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(entry.path, style = MaterialTheme.typography.bodyMedium)
                        Text("${entry.size} B · ${entry.modified}", style = MaterialTheme.typography.bodySmall)
                    }
                    Text("Download", style = MaterialTheme.typography.labelSmall)
                }
            }
            if (loading) item { Text("Loading...") }
        }
        preview?.let { bitmap ->
            Image(bitmap = bitmap, contentDescription = "Remote image", modifier = Modifier.fillMaxWidth())
        }
    }
}

@Composable
private fun CameraPage() {
    var facing by remember { mutableStateOf(0) }
    var status by remember { mutableStateOf("Ready") }
    val service = remember { Python.getInstance().getModule("client_service") }
    val scope = rememberCoroutineScope()
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { facing = 0 }) { Text("Back") }
            Button(onClick = { facing = 1 }) { Text("Front") }
            Button(onClick = {
                status = "Capturing..."
                scope.launch {
                    val result = withContext(Dispatchers.IO) {
                        service.callAttr("call_feature", "camera", "capture", facing).toString()
                    }
                    status = result
                }
            }) { Text("Capture") }
        }
        Text(status)
        Text("JPEG stays in memory on the target and is transferred outside MQTT.", style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun WifiPage() {
    var status by remember { mutableStateOf("Waiting for target RPC") }
    val service = remember { Python.getInstance().getModule("client_service") }
    val scope = rememberCoroutineScope()
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Button(onClick = {
            status = "Querying..."
            scope.launch {
                status = withContext(Dispatchers.IO) {
                    service.callAttr("call_feature", "wifi", "info").toString()
                }
            }
        }) { Text("Refresh Wi-Fi") }
        Text(status, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun LogsPage() {
    LazyColumn(Modifier.fillMaxSize().padding(16.dp)) {
        item { Text("No requests yet", style = MaterialTheme.typography.bodyMedium) }
    }
}

@Composable
private fun DynamicFeaturePage(feature: FeatureDescriptor) {
    var result by remember(feature.name) { mutableStateOf("Ready") }
    val service = remember { Python.getInstance().getModule("client_service") }
    val scope = rememberCoroutineScope()
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(feature.title, style = MaterialTheme.typography.headlineSmall)
        Text("feature_${feature.name}.py · actions=${feature.actions.joinToString()}", style = MaterialTheme.typography.bodySmall)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            feature.actions.forEach { action ->
                Button(onClick = {
                    result = "Running $action..."
                    scope.launch {
                        result = withContext(Dispatchers.IO) {
                            runCatching { service.callAttr("call_feature", feature.name, action).toString() }
                                .getOrElse { "Error: ${it.message}" }
                        }
                    }
                }) { Text(action) }
            }
        }
        Text(result, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun SettingsPage(
    modifier: Modifier = Modifier,
    onBack: () -> Unit,
    onDeviceChanged: (String) -> Unit,
    onPermissions: () -> Unit
) {
    val context = androidx.compose.ui.platform.LocalContext.current
    var topic by remember { mutableStateOf("sys/device/request") }
    var remoteRoot by remember { mutableStateOf("/data/data") }
    var domain by remember { mutableStateOf("") }
    var token by remember { mutableStateOf("") }
    var useExternal by remember {
        mutableStateOf(context.getSharedPreferences("client_mqtt", Context.MODE_PRIVATE).getBoolean("use_external_scripts", false))
    }
    var status by remember { mutableStateOf("") }
    val externalAllowed = Build.VERSION.SDK_INT < Build.VERSION_CODES.R || Environment.isExternalStorageManager()
    val scriptRoot = if (useExternal && externalAllowed) "/sdcard/apm/client_mqtt" else "${context.filesDir}/client_mqtt"
    val service = remember { Python.getInstance().getModule("client_service") }
    Column(modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Settings", style = MaterialTheme.typography.headlineSmall)
            Button(onClick = onBack) { Text("Done") }
        }
        OutlinedTextField(topic, { topic = it; onDeviceChanged(it.substringAfterLast('/')) }, Modifier.fillMaxWidth(), label = { Text("Request topic") })
        OutlinedTextField(remoteRoot, { remoteRoot = it }, Modifier.fillMaxWidth(), label = { Text("Allowed remote root") })
        OutlinedTextField(domain, { domain = it }, Modifier.fillMaxWidth(), label = { Text("Aliyun domain") })
        OutlinedTextField(token, { token = it }, Modifier.fillMaxWidth(), label = { Text("Aliyun token") })
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Column(Modifier.weight(1f)) {
                Text("Script directory", style = MaterialTheme.typography.labelLarge)
                Text(scriptRoot, style = MaterialTheme.typography.bodySmall)
                Text(if (externalAllowed) "External storage is authorized" else "Using internal storage; authorize all files to use /sdcard/apm/client_mqtt/", style = MaterialTheme.typography.bodySmall)
            }
            Switch(checked = useExternal, onCheckedChange = {
                useExternal = it
                context.getSharedPreferences("client_mqtt", Context.MODE_PRIVATE).edit().putBoolean("use_external_scripts", it).apply()
                status = "Restart the app to apply script directory"
            })
        }
        Button(onClick = onPermissions) {
            Icon(Icons.TwoTone.Security, contentDescription = null)
            Text("All Android permissions")
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = {
                service.callAttr("update_settings", "{\"aliyun\":{\"domain\":${JSONObject.quote(domain)},\"token\":${JSONObject.quote(token)}},\"remote_root\":${JSONObject.quote(remoteRoot)}}")
                status = "Saved to $scriptRoot/client_mqtt.json"
            }) { Text("Save settings") }
            Text(status, style = MaterialTheme.typography.bodySmall)
        }
        Text("Private keys and tokens are stored in the selected script directory and never logged.", style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun PermissionPage(onBack: () -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current
    var refresh by remember { mutableStateOf(0) }
    var status by remember { mutableStateOf("") }
    val candidates = remember {
        listOf(
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.READ_CONTACTS,
            Manifest.permission.WRITE_CONTACTS,
            Manifest.permission.READ_CALENDAR,
            Manifest.permission.WRITE_CALENDAR,
            Manifest.permission.READ_PHONE_STATE,
            Manifest.permission.CALL_PHONE,
            Manifest.permission.SEND_SMS,
            Manifest.permission.RECEIVE_SMS,
            Manifest.permission.BLUETOOTH_CONNECT,
            Manifest.permission.BLUETOOTH_SCAN,
            Manifest.permission.BLUETOOTH_ADVERTISE,
            Manifest.permission.POST_NOTIFICATIONS,
            Manifest.permission.READ_MEDIA_IMAGES,
            Manifest.permission.READ_MEDIA_VIDEO,
            Manifest.permission.READ_MEDIA_AUDIO,
            Manifest.permission.READ_EXTERNAL_STORAGE,
            Manifest.permission.WRITE_EXTERNAL_STORAGE
        ).filter { permission ->
            when {
                permission.startsWith("android.permission.BLUETOOTH_") -> Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
                permission.startsWith("android.permission.READ_MEDIA_") -> Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                permission == Manifest.permission.POST_NOTIFICATIONS -> Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                permission == Manifest.permission.READ_EXTERNAL_STORAGE -> Build.VERSION.SDK_INT <= Build.VERSION_CODES.S_V2
                permission == Manifest.permission.WRITE_EXTERNAL_STORAGE -> Build.VERSION.SDK_INT <= Build.VERSION_CODES.Q
                else -> true
            }
        }
    }
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        refresh++
        status = "授权完成：${result.count { it.value }} / ${result.size}"
    }
    val settingsLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { refresh++ }
    val allFilesGranted = Build.VERSION.SDK_INT < Build.VERSION_CODES.R || Environment.isExternalStorageManager()
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("All permissions", style = MaterialTheme.typography.headlineSmall)
            Button(onClick = onBack) { Text("Back") }
        }
        Button(onClick = { permissionLauncher.launch(candidates.toTypedArray()) }) {
            Icon(Icons.TwoTone.Security, contentDescription = null)
            Text("Request all runtime permissions")
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Button(onClick = {
                settingsLauncher.launch(Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:${context.packageName}")))
            }) {
                Text(if (allFilesGranted) "All files access granted" else "Authorize all files access")
            }
        }
        Text("Script storage defaults to internal app storage. After all-files access is granted, enable external scripts in the previous page to use /sdcard/apm/client_mqtt/.", style = MaterialTheme.typography.bodySmall)
        Text(status, style = MaterialTheme.typography.labelMedium)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            items(candidates) { permission ->
                val granted = ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
                Text("${if (granted) "OK" else "--"}  ${permission.removePrefix("android.permission.")}")
            }
        }
    }
}
