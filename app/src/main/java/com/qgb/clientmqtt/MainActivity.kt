package com.qgb.clientmqtt

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
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
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.snapshotFlow
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.chaquo.python.Python
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

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
    val pages = listOf("Files", "Camera", "Wi-Fi", "Logs")
    val pagerState = rememberPagerState(pageCount = { pages.size })
    val pagerScope = rememberCoroutineScope()
    var settings by remember { mutableStateOf(false) }
    var selectedDevice by remember { mutableStateOf("Target") }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(selectedDevice) },
                actions = {
                    IconButton(onClick = { settings = true }) {
                        Icon(Icons.Outlined.Settings, contentDescription = "Settings")
                    }
                }
            )
        }
    ) { padding ->
        if (settings) {
            SettingsPage(
                modifier = Modifier.padding(padding),
                onBack = { settings = false },
                onDeviceChanged = { selectedDevice = it }
            )
        } else {
            Column(modifier = Modifier.fillMaxSize().padding(padding)) {
                ScrollableTabRow(selectedTabIndex = pagerState.currentPage) {
                    pages.forEachIndexed { index, page ->
                        Tab(
                            selected = pagerState.currentPage == index,
                            onClick = { pagerScope.launch { pagerState.animateScrollToPage(index) } },
                            text = { Text(page) },
                            icon = {
                                Icon(
                                    imageVector = when (index) {
                                        0 -> Icons.Outlined.Folder
                                        1 -> Icons.Outlined.CameraAlt
                                        2 -> Icons.Outlined.NetworkWifi
                                        else -> Icons.Outlined.Settings
                                    },
                                    contentDescription = page
                                )
                            }
                        )
                    }
                }
                HorizontalPager(state = pagerState, modifier = Modifier.fillMaxSize()) { page ->
                    when (page) {
                        0 -> FilesPage()
                        1 -> CameraPage()
                        2 -> WifiPage()
                        else -> LogsPage()
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
    var entries by remember { mutableStateOf(listOf<String>()) }
    var nextOffset by remember { mutableStateOf(0) }
    var hasMore by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(false) }
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
                        add("${item.optString("path")}  ${item.optLong("size")} B  ${item.optDouble("modified")}")
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
            items(entries) { entry -> Text(entry, style = MaterialTheme.typography.bodySmall) }
            if (loading) item { Text("Loading...") }
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
private fun SettingsPage(
    modifier: Modifier = Modifier,
    onBack: () -> Unit,
    onDeviceChanged: (String) -> Unit
) {
    var topic by remember { mutableStateOf("sys/device/request") }
    var remoteRoot by remember { mutableStateOf("/data/data") }
    var domain by remember { mutableStateOf("") }
    Column(modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Settings", style = MaterialTheme.typography.headlineSmall)
            Button(onClick = onBack) { Text("Done") }
        }
        OutlinedTextField(topic, { topic = it; onDeviceChanged(it.substringAfterLast('/')) }, Modifier.fillMaxWidth(), label = { Text("Request topic") })
        OutlinedTextField(remoteRoot, { remoteRoot = it }, Modifier.fillMaxWidth(), label = { Text("Allowed remote root") })
        OutlinedTextField(domain, { domain = it }, Modifier.fillMaxWidth(), label = { Text("Aliyun domain") })
        Text("Private keys and tokens are stored in app-private configuration and never logged.", style = MaterialTheme.typography.bodySmall)
    }
}
