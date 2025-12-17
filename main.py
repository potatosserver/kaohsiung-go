import sys
import json
import requests
import time
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLineEdit, QPushButton, QListWidget, QListWidgetItem, 
                             QLabel, QFrame, QScrollArea, QHBoxLayout, QCheckBox, 
                             QDialog, QGraphicsDropShadowEffect, QGridLayout, 
                             QSizePolicy, QAbstractItemView)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QThread, Qt, QTimer, QSize, QRect, QPropertyAnimation, QEasingCurve, QPoint, QRectF
from PyQt6.QtGui import QColor, QFontDatabase, QFont, QCursor, QIcon, QPainter, QFontMetrics, QPen, QBrush

CONFIG = {
    'UBIKE_LIST': 'https://apis.youbike.com.tw/json/station-min-yb2.json',
    'UBIKE_REALTIME': 'https://apis.youbike.com.tw/tw2/parkingInfo',
    'IBUS_API': 'https://ibus.tbkc.gov.tw/ibus/graphql',
    'METRO_STATIONS': 'https://traffic.tbkc.gov.tw/api/metro/stations',
    'LRT_STATIONS': 'https://traffic.tbkc.gov.tw/api/lrts',
    'METRO_LIVE': 'https://traffic.tbkc.gov.tw/api/metro/live-boards?language=zh-TW',
    'LRT_LIVE': 'https://traffic.tbkc.gov.tw/api/lrts/live-boards?language=zh-TW',
    'HEADERS': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.youbike.com.tw/',
        'Origin': 'https://www.youbike.com.tw'
    }
}

ICONS = {
    'search': '\ue8b6', 'my_location': '\ue55c', 'place': '\ue55f', 'refresh': '\ue5d5',
    'layers': '\ue53b', 'close': '\ue5cd', 'directions_bus': '\ue530', 'pedal_bike': '\ueb29',
    'bolt': '\uea0b', 'local_parking': '\ue54f', 'tram': '\ue571', 'schedule': '\ue8b5',
    'chevron_right': '\ue5cc', 'campaign': '\uef49', 'bus_alert': '\ue98f', 'gps_fixed': '\ue1b3',
    'arrow_back': '\ue5c4', 'cancel': '\ue5c9', 'check': '\ue876'
}

MAP_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster/dist/MarkerCluster.Default.css" />
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons+Round" rel="stylesheet">
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster/dist/leaflet.markercluster.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        body, html, #map { height: 100%; margin: 0; overflow: hidden; background: #f3f4f6; font-family: 'Noto Sans TC', sans-serif; }
        .custom-icon { 
            border-radius: 50%; display: flex; justify-content: center; align-items: center; 
            box-shadow: 0 4px 8px rgba(0,0,0,0.4); border: 2px solid white; color: white; 
            transition: transform 0.2s; cursor: pointer; box-sizing: border-box; overflow: hidden; 
        }
        .custom-icon:hover { transform: scale(1.15); z-index: 1000 !important; }
        .bus-icon { background: #2563eb; }
        .ubike-icon { background: #ffd500; color: black !important; }
        .line-bg-R { background-color: #ff0000; }
        .line-bg-O { background-color: #ff8400; }
        .line-bg-C { background-color: #16a34a; }
        .metro-text { font-weight: 900; font-size: 14px; font-family: sans-serif; line-height: 1; }
        .marker-cluster div { color: white !important; border-radius: 50%; width: 30px; height: 30px; margin-left: 5px; margin-top: 5px; text-align: center; line-height: 30px; font-weight: bold; font-family: sans-serif; }
        .marker-cluster-bus { background-color: rgba(37, 99, 235, 0.5); } .marker-cluster-bus div { background-color: #2563eb; }
        .marker-cluster-bike { background-color: rgba(255, 213, 0, 0.5); } .marker-cluster-bike div { background-color: #ffd500; color: black !important; }
        .marker-cluster-metro-r { background-color: rgba(255, 0, 0, 0.5); } .marker-cluster-metro-r div { background-color: #ff0000; }
        .marker-cluster-metro-o { background-color: rgba(255, 132, 0, 0.5); } .marker-cluster-metro-o div { background-color: #ff8400; }
        .marker-cluster-lrt { background-color: rgba(22, 163, 74, 0.5); } .marker-cluster-lrt div { background-color: #16a34a; }
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map, layers = {}, backend;
        function initMap() {
            map = L.map('map', {zoomControl: false}).setView([22.631442, 120.301890], 13);
            L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', { maxZoom: 19, attribution: '' }).addTo(map);
            new QWebChannel(qt.webChannelTransport, function(channel) { backend = channel.objects.backend; });
            map.on('click', function() { if(backend) backend.onMapClicked(); });
        }
        function createCluster(name, className) {
            layers[name] = L.markerClusterGroup({
                showCoverageOnHover: false, maxClusterRadius: 80,
                iconCreateFunction: function(c) { return L.divIcon({ html: '<div>' + c.getChildCount() + '</div>', className: 'marker-cluster ' + className, iconSize: [40, 40] }); }
            });
            map.addLayer(layers[name]);
        }
        function addMarkers(layerName, markersData) {
            if (!layers[layerName]) return;
            var markers = [];
            markersData.forEach(function(d) {
                var iconClass = 'custom-icon '; var content = '';
                if (layerName === 'bus') { iconClass += 'bus-icon'; content = '<span class="material-icons-round" style="font-size:18px;">directions_bus</span>'; }
                else if (layerName === 'bike') { iconClass += 'ubike-icon'; content = '<span class="material-icons-round" style="font-size:18px;">pedal_bike</span>'; }
                else { var line = d.id.charAt(0).toUpperCase(); iconClass += 'line-bg-' + line; content = '<span class="metro-text">' + line + '</span>'; }
                var icon = L.divIcon({ className: iconClass, html: content, iconSize: [30, 30] });
                var marker = L.marker([d.lat, d.lon], {icon: icon});
                marker.on('click', function(e) { L.DomEvent.stopPropagation(e); if(backend) backend.onMarkerClicked(d.type, d.id, d.name, d.lat, d.lon, d.addr || ""); });
                markers.push(marker);
            });
            layers[layerName].addLayers(markers);
        }
        function clearLayer(name) { if (layers[name]) layers[name].clearLayers(); }
        function flyToOffset(lat, lon, zoom, offsetX, offsetY) {
            var targetPoint = map.project([lat, lon], zoom);
            var newCenterPoint = targetPoint.subtract([offsetX, offsetY]);
            var newCenter = map.unproject(newCenterPoint, zoom);
            map.flyTo(newCenter, zoom, {animate: true, duration: 0.8});
        }
        initMap();
        ['bus','bike','metroR','metroO','lrt'].forEach(n => createCluster(n, 'marker-cluster-' + (n.startsWith('metro') ? n.replace('R','-r').replace('O','-o') : n)));
    </script>
</body>
</html>
"""

class FontLoader:
    @staticmethod
    def load_material_icons():
        print("正在下載 Material Icons (1/5)...")
        font_url = "https://github.com/google/material-design-icons/raw/master/font/MaterialIcons-Regular.ttf"
        font_path = os.path.join(os.getcwd(), "MaterialIcons-Regular.ttf")
        if not os.path.exists(font_path):
            try:
                r = requests.get(font_url)
                with open(font_path, 'wb') as f: f.write(r.content)
            except: 
                print("Material Icons 下載失敗"); return "Arial"
        font_id = QFontDatabase.addApplicationFont(font_path)
        return QFontDatabase.applicationFontFamilies(font_id)[0] if font_id != -1 else "Arial"

class DataLoader(QThread):
    data_loaded = pyqtSignal(dict)
    def run(self):
        result = {'bus': [], 'bike': [], 'metro': []}
        print("正在下載公車路線 (2/5)...")
        try:
            q = """query { routes(lang: "zh") { edges { node { id } } } }"""
            rids = [x['node']['id'] for x in requests.post(CONFIG['IBUS_API'], json={'query': q}).json()['data']['routes']['edges']][:60]
        except Exception as e: print(f"Bus Route Error: {e}"); rids = []

        print("正在下載公車所有站點 (3/5)...")
        try:
            if rids:
                qs = [f'r_{i}: route(xno: {i}, lang: "zh") {{ stations {{ edges {{ node {{ id name lat lon }} }} }} }}' for i in rids]
                raw = requests.post(CONFIG['IBUS_API'], json={'query': "query{" + "\n".join(qs) + "}"}).json().get('data', {})
                stops = {}
                for v in raw.values():
                    if v and v.get('stations'):
                        for e in v['stations']['edges']:
                            n = e['node']; 
                            if n['id'] not in stops and n['lat']: stops[n['id']] = {'id': n['id'], 'name': n['name'], 'lat': n['lat'], 'lon': n['lon'], 'type': 'bus'}
                result['bus'] = list(stops.values())
        except Exception as e: print(f"Bus Stops Error: {e}")

        print("正在下載 YouBike 站點 (4/5)...")
        try:
            b = requests.get(CONFIG['UBIKE_LIST']).json()
            result['bike'] = [{'id': s['station_no'], 'name': s['name_tw'], 'lat': float(s['lat']), 'lon': float(s['lng']), 'addr': s['address_tw'], 'type': 'bike'} for s in b if float(s['lat']) > 22.4]
        except Exception as e: print(f"Bike Error: {e}")

        print("正在下載捷運路線 (5/5)...")
        try:
            m = requests.get(CONFIG['METRO_STATIONS']).json(); l = requests.get(CONFIG['LRT_STATIONS']).json()
            all_m = []
            for s in m + l:
                pos = s.get('position', {}); lat, lon = pos.get('lat'), pos.get('lng') or pos.get('lon')
                if lat and lon: all_m.append({'id': s['id'], 'name': s['name'], 'lat': lat, 'lon': lon, 'type': 'metro'})
            result['metro'] = all_m
        except Exception as e: print(f"Metro Error: {e}")
        print("所有資料載入完成！")
        self.data_loaded.emit(result)

class RealtimeFetcher(QThread):
    info_updated = pyqtSignal(dict)
    def __init__(self, t, i, n): super().__init__(); self.t, self.i, self.n = t, i, n
    def run(self):
        t_map = {'bus': '公車', 'bike': 'YouBike', 'metro': '捷運/輕軌'}
        print(f"正在載入 {t_map.get(self.t, self.t)} [{self.n} (ID: {self.i})] 的即時資料...")
        try:
            d = None
            if self.t == 'bus':
                q1 = """query Q($ids:[Int!]!){stations(lang:"zh",ids:$ids){edges{node{... on Station{routes{edges{goBack node{id name}}}}}}}}"""
                r1 = requests.post(CONFIG['IBUS_API'], json={'query': q1, 'variables': {'ids': [int(self.i)]}}).json()
                routes = r1.get('data', {}).get('stations', {}).get('edges', [])[0].get('node', {}).get('routes', {}).get('edges', [])
                if routes:
                    ins = [{'xno': int(e['node']['id']), 'goBack': int(e['goBack']), 'stationId': int(self.i)} for e in routes]
                    q2 = """query T($t:[EstimateStationInput!]!){stationEstimates(targets:$t){edges{node{comeTime isSuspended etas{etaTime}}}}}"""
                    ests = requests.post(CONFIG['IBUS_API'], json={'query': q2, 'variables': {'t': ins}}).json().get('data', {}).get('stationEstimates', {}).get('edges', [])
                    d = [{'name': r['node']['name'], 'dir': '去程' if r['goBack']==1 else '返程', 'susp': ests[i]['node'].get('isSuspended'), 'ct': ests[i]['node'].get('comeTime'), 'eta': (ests[i]['node'].get('etas') or [{}])[0].get('etaTime')} for i, r in enumerate(routes)]
            elif self.t == 'bike':
                r = requests.post(CONFIG['UBIKE_REALTIME'], json={'station_no': [self.i]}, headers=CONFIG['HEADERS'])
                if r.ok: d = r.json().get('retVal', {}).get('data', [])[0]
            elif self.t == 'metro':
                m = requests.get(CONFIG['METRO_LIVE']).json() + requests.get(CONFIG['LRT_LIVE']).json()
                d = [x for x in m if x['stationId'] == self.i]
            self.info_updated.emit({'type': self.t, 'data': d}); print(f"-> {self.n} 資料更新完成")
        except Exception as e: print(f"!! {self.n} 載入失敗: {e}"); self.info_updated.emit({'type': self.t, 'data': None})

class BackendBridge(QObject):
    markerClicked = pyqtSignal(str, str, str, float, float, str)
    mapClicked = pyqtSignal()
    @pyqtSlot(str, str, str, float, float, str)
    def onMarkerClicked(self, t, i, n, la, lo, a): self.markerClicked.emit(t, i, n, la, lo, a)
    @pyqtSlot()
    def onMapClicked(self): self.mapClicked.emit()

class IconLabel(QLabel):
    def __init__(self, icon_name, size=24, color="black"):
        super().__init__()
        self.setFont(QFont(MATERIAL_FONT_FAMILY, size))
        self.setText(ICONS.get(icon_name, '?'))
        self.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        self.setFixedSize(size+10, size+10)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

class ElidedLabel(QLabel):
    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(self.rect(), self.alignment(), elided)

class CountdownButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # 移除 CSS 的背景與邊框，完全由 paintEvent 控制
        self.setStyleSheet("background: transparent; border: none;")
        
        self.icon_lbl = IconLabel('refresh', 20, "#64748b")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_progress)
        self.duration = 30000
        self.elapsed = 0
        self.is_running = False

    def start_countdown(self, duration_ms=30000):
        self.duration = duration_ms
        self.elapsed = 0
        self.is_running = True
        self.timer.start()
        self.icon_lbl.setStyleSheet("color: #3b82f6;")
        self.update()

    def stop_countdown(self):
        self.is_running = False
        self.timer.stop()
        self.icon_lbl.setStyleSheet("color: #64748b;")
        self.update()

    def update_progress(self):
        self.elapsed += 50
        if self.elapsed >= self.duration:
            self.elapsed = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#f8fafc")))
        painter.drawEllipse(2, 2, 36, 36)
        
        pen_grey = QPen(QColor("#e2e8f0"), 2)
        painter.setPen(pen_grey)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(2, 2, 36, 36)

        if self.is_running:
            pen_blue = QPen(QColor("#3b82f6"), 2)
            pen_blue.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_blue)
            
            rect = QRectF(2, 2, 36, 36)
            progress = 1.0 - (self.elapsed / self.duration)
            span_angle = int(progress * 360 * 16)
            start_angle = 90 * 16 
            painter.drawArc(rect, start_angle, span_angle)

class LayerCheckbox(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent); self.setCheckable(True); self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFixedSize(24, 24)
        self.setStyleSheet(f"""
            QPushButton {{ background-color: white; border: 2px solid #cbd5e1; border-radius: 6px; color: transparent; }}
            QPushButton:checked {{ background-color: #2563eb; border: 2px solid #2563eb; color: white; font-family: "{MATERIAL_FONT_FAMILY}"; font-size: 18px; }}
        """)
        self.setText(ICONS['check'])

class SettingsDialog(QDialog):
    def __init__(self, parent, settings, callback):
        super().__init__(parent); self.settings, self.callback = settings, callback
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground); self.resize(320, 400)
        main_frame = QFrame(self); main_frame.setGeometry(0, 0, 320, 400)
        main_frame.setStyleSheet("QFrame { background-color: white; border-radius: 24px; }")
        shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(40); shadow.setColor(QColor(0,0,0,80)); main_frame.setGraphicsEffect(shadow)
        layout = QVBoxLayout(main_frame); layout.setContentsMargins(24, 24, 24, 24)
        header = QHBoxLayout(); title = QLabel("圖層設定"); title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1e293b;")
        close_btn = QPushButton(); close_btn.setFixedSize(30, 30); close_btn.setIcon(QIcon()); close_btn.setStyleSheet("background: #f1f5f9; border-radius: 15px; border: none;")
        cl = QVBoxLayout(close_btn); cl.setContentsMargins(0,0,0,0); cl.addWidget(IconLabel('close', 20, "#64748b"), 0, Qt.AlignmentFlag.AlignCenter)
        close_btn.clicked.connect(self.close); header.addWidget(title); header.addStretch(); header.addWidget(close_btn); layout.addLayout(header); layout.addSpacing(10)
        options = [('bus', '公車', 'directions_bus', '#2563eb', '#dbeafe'), ('bike', 'YouBike 2.0', 'pedal_bike', '#b45309', '#fef3c7'),
                   ('metroR', '捷運紅線', 'tram', '#b91c1c', '#fee2e2'), ('metroO', '捷運橘線', 'tram', '#c2410c', '#ffedd5'), ('lrt', '環狀輕軌', 'tram', '#15803d', '#dcfce7')]
        for key, name, icon, fg, bg in options:
            row = QFrame(); row.setStyleSheet(f"background: #f8fafc; border-radius: 12px;"); rl = QHBoxLayout(row); rl.setContentsMargins(12, 10, 12, 10)
            ic_frame = QFrame(); ic_frame.setFixedSize(36, 36); ic_frame.setStyleSheet(f"background: {bg}; border-radius: 18px;")
            il = QVBoxLayout(ic_frame); il.setContentsMargins(0,0,0,0); il.addWidget(IconLabel(icon, 18, fg), 0, Qt.AlignmentFlag.AlignCenter)
            lbl = QLabel(name); lbl.setStyleSheet("font-size: 15px; font-weight: 500; color: #334155; margin-left: 8px;")
            chk = LayerCheckbox(); chk.setChecked(self.settings[key]); chk.toggled.connect(lambda s, k=key: (self.settings.update({k: s}), self.callback()))
            rl.addWidget(ic_frame); rl.addWidget(lbl); rl.addStretch(); rl.addWidget(chk); layout.addWidget(row)
        layout.addStretch()
    def mousePressEvent(self, e): 
        if e.button() == Qt.MouseButton.LeftButton: self.drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft(); e.accept()
    def mouseMoveEvent(self, e): 
        if e.buttons() == Qt.MouseButton.LeftButton: self.move(e.globalPosition().toPoint() - self.drag_pos); e.accept()

class SearchResultItem(QWidget):
    def __init__(self, icon_key, bg_color, text_color, title, subtitle):
        super().__init__()
        layout = QHBoxLayout(self); layout.setContentsMargins(10, 8, 10, 8)
        icon_frame = QFrame(); icon_frame.setFixedSize(40, 40); icon_frame.setStyleSheet(f"background-color: {bg_color}; border-radius: 20px; border: none;")
        il = QVBoxLayout(icon_frame); il.setContentsMargins(0,0,0,0); il.addWidget(IconLabel(icon_key, 20, text_color), 0, Qt.AlignmentFlag.AlignCenter)
        text_layout = QVBoxLayout(); text_layout.setSpacing(2)
        t_lbl = QLabel(title); t_lbl.setStyleSheet("font-weight: bold; font-size: 14px; background: transparent; border: none;")
        s_lbl = QLabel(subtitle); s_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; background: transparent; border: none;")
        text_layout.addWidget(t_lbl); text_layout.addWidget(s_lbl)
        layout.addWidget(icon_frame); layout.addLayout(text_layout); layout.addStretch(); self.setStyleSheet("background-color: transparent;")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        global MATERIAL_FONT_FAMILY; MATERIAL_FONT_FAMILY = FontLoader.load_material_icons()
        self.setWindowTitle("高雄交通智慧地圖"); self.resize(1280, 800)
        
        self.web = QWebEngineView(); self.chn = QWebChannel(); self.brg = BackendBridge()
        self.brg.markerClicked.connect(self.open_sidebar); self.brg.mapClicked.connect(self.close_sidebar)
        self.chn.registerObject("backend", self.brg); self.web.page().setWebChannel(self.chn)
        self.web.page().featurePermissionRequested.connect(lambda u, f: self.web.page().setFeaturePermission(u, f, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser))
        self.web.setHtml(MAP_HTML); self.setCentralWidget(self.web)
        
        self.setup_ui()
        self.data, self.settings = {}, {'bus': True, 'bike': True, 'metroR': True, 'metroO': True, 'lrt': True}
        self.loader = DataLoader(); self.loader.data_loaded.connect(self.on_loaded); self.loader.start()
        self.timer = QTimer(); self.timer.timeout.connect(lambda: self.refresh_data(auto=True))
        
        self.search_anim = QPropertyAnimation(self.search_box, b"pos"); self.search_anim.setDuration(300); self.search_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.res_anim = QPropertyAnimation(self.search_results, b"pos"); self.res_anim.setDuration(300); self.res_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def setup_ui(self):
        self.search_box = QFrame(self); self.search_box.setStyleSheet("QFrame { background-color: white; border-radius: 24px; border: none; }")
        shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0,0,0,30)); shadow.setOffset(0, 4); self.search_box.setGraphicsEffect(shadow)
        sb_layout = QHBoxLayout(self.search_box); sb_layout.setContentsMargins(15, 5, 15, 5)
        sb_layout.addWidget(IconLabel('search', 22, "#94a3b8"))
        self.search_input = QLineEdit(); self.search_input.setPlaceholderText("搜尋公車、捷運、YouBike...")
        self.search_input.setStyleSheet("QLineEdit { border: none; font-size: 16px; background: transparent; padding: 5px; }"); self.search_input.textChanged.connect(self.update_search)
        sb_layout.addWidget(self.search_input)
        self.clear_btn = QPushButton(); self.clear_btn.setIcon(QIcon()); cl_layout = QVBoxLayout(self.clear_btn); cl_layout.setContentsMargins(0,0,0,0)
        cl_layout.addWidget(IconLabel('cancel', 20, "#cbd5e1"), 0, Qt.AlignmentFlag.AlignCenter); self.clear_btn.setFixedSize(30, 30)
        self.clear_btn.setStyleSheet("background: transparent; border: none;"); self.clear_btn.clicked.connect(lambda: (self.search_input.clear(), self.search_results.hide()))
        self.clear_btn.hide(); sb_layout.addWidget(self.clear_btn)

        self.search_results = QListWidget(self); self.search_results.hide(); self.search_results.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.search_results.setStyleSheet("QListWidget { background-color: white; border-radius: 16px; border: none; outline: none; } QListWidget::item { border-bottom: 1px solid #f1f5f9; padding: 0px; } QListWidget::item:selected { background-color: #f8fafc; }")
        res_shadow = QGraphicsDropShadowEffect(); res_shadow.setBlurRadius(30); res_shadow.setColor(QColor(0,0,0,40)); res_shadow.setOffset(0, 10); self.search_results.setGraphicsEffect(res_shadow)
        self.search_results.itemClicked.connect(self.on_search_result_clicked)

        self.sidebar = QFrame(self); self.sidebar.hide(); self.sidebar.setStyleSheet("QFrame#Sidebar { background-color: #f8fafc; border-top-left-radius: 28px; border-top-right-radius: 28px; border: none; }"); self.sidebar.setObjectName("Sidebar")
        sb_shadow = QGraphicsDropShadowEffect(); sb_shadow.setBlurRadius(50); sb_shadow.setColor(QColor(0,0,0,60)); self.sidebar.setGraphicsEffect(sb_shadow)
        main_layout = QVBoxLayout(self.sidebar); main_layout.setContentsMargins(0,0,0,0); main_layout.setSpacing(0)
        header = QFrame(); header.setStyleSheet("background-color: white; border-top-left-radius: 28px; border-top-right-radius: 28px; border-bottom: 1px solid #e2e8f0;")
        hl = QHBoxLayout(header); hl.setContentsMargins(24, 20, 24, 20)
        info_layout = QVBoxLayout(); info_layout.setSpacing(4)
        self.sb_badge = QLabel(); self.sb_badge.setStyleSheet("font-weight: bold; border-radius: 6px; padding: 2px 8px; font-size: 12px;")
        info_layout.addWidget(self.sb_badge, 0, Qt.AlignmentFlag.AlignLeft)
        self.sb_title = QLabel(); self.sb_title.setStyleSheet("font-size: 20px; font-weight: 900; color: #1e293b; border: none;"); self.sb_title.setWordWrap(True)
        self.sb_sub = QLabel(); self.sb_sub.setStyleSheet("color: #64748b; font-size: 13px; border: none;")
        info_layout.addWidget(self.sb_title); info_layout.addWidget(self.sb_sub)
        self.refresh_btn = CountdownButton() # [FIX] Updated button
        self.refresh_btn.clicked.connect(self.refresh_data)
        hl.addLayout(info_layout); hl.addWidget(self.refresh_btn); main_layout.addWidget(header)
        self.scroll_area = QScrollArea(); self.scroll_area.setWidgetResizable(True); self.scroll_area.setFrameShape(QFrame.Shape.NoFrame); self.scroll_area.setStyleSheet("background-color: transparent; border: none;")
        self.sb_content = QWidget(); self.sb_content.setStyleSheet("background-color: #f8fafc;")
        self.sb_layout = QVBoxLayout(self.sb_content); self.sb_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sb_layout.setContentsMargins(20, 20, 20, 80); self.sb_layout.setSpacing(12)
        self.scroll_area.setWidget(self.sb_content); main_layout.addWidget(self.scroll_area)

        self.settings_btn = QPushButton(self); self.settings_btn.setFixedSize(56, 56)
        self.settings_btn.setStyleSheet("QPushButton { background-color: white; border-radius: 28px; border: none; } QPushButton:hover { background-color: #eff6ff; }")
        btn_shadow = QGraphicsDropShadowEffect(); btn_shadow.setBlurRadius(20); btn_shadow.setColor(QColor(0,0,0,40)); btn_shadow.setOffset(0,4); self.settings_btn.setGraphicsEffect(btn_shadow)
        sl = QVBoxLayout(self.settings_btn); sl.addWidget(IconLabel('layers', 24, "#475569"), 0, Qt.AlignmentFlag.AlignCenter); self.settings_btn.clicked.connect(self.open_settings)

    def open_settings(self):
        d = SettingsDialog(self, self.settings, self.apply_layers)
        d.exec()

    def resizeEvent(self, event):
        self.update_layout_state()
        self.settings_btn.move(self.width() - 80, self.height() - 80)

    def update_layout_state(self):
        w, h = self.width(), self.height()
        sidebar_w, sidebar_gap = 380, 24
        if self.sidebar.isVisible():
            if w > h: 
                self.sidebar.setGeometry(sidebar_gap, sidebar_gap, sidebar_w, h - (sidebar_gap*2))
                search_target_x = sidebar_gap + sidebar_w + 20
            else: 
                self.sidebar.setGeometry(0, int(h*0.4), w, int(h*0.6))
                search_target_x = 24
        else:
            search_target_x = 24

        search_w = min(400, w - search_target_x - 24)
        self.search_box.setFixedSize(search_w, 52)
        self.search_results.setFixedWidth(search_w)
        if self.search_box.pos().x() != search_target_x:
            self.search_anim.setEndValue(QPoint(search_target_x, 24)); self.search_anim.start()
            self.res_anim.setEndValue(QPoint(search_target_x, 84)); self.res_anim.start()
        else:
            self.search_box.move(search_target_x, 24); self.search_results.move(search_target_x, 84)

    def pan_map_to_offset(self, lat, lon):
        w, h = self.width(), self.height()
        offset_x, offset_y = 0, 0
        if self.sidebar.isVisible():
            if w > h: offset_x = 190
            else: offset_y = -(h * 0.3)
        self.web.page().runJavaScript(f"flyToOffset({lat}, {lon}, 18, {offset_x}, {offset_y})")

    def on_loaded(self, data):
        self.data = data; self.apply_layers()

    def apply_layers(self):
        for k in ['bus', 'bike', 'metroR', 'metroO', 'lrt']: self.web.page().runJavaScript(f"clearLayer('{k}')")
        if self.settings['bus']: self.web.page().runJavaScript(f"addMarkers('bus', {json.dumps(self.data['bus'])})")
        if self.settings['bike']: self.web.page().runJavaScript(f"addMarkers('bike', {json.dumps(self.data['bike'])})")
        if any([self.settings['metroR'], self.settings['metroO'], self.settings['lrt']]):
            r = [s for s in self.data['metro'] if s['id'].startswith('R')]
            o = [s for s in self.data['metro'] if s['id'].startswith('O')]
            c = [s for s in self.data['metro'] if s['id'].startswith('C')]
            if self.settings['metroR']: self.web.page().runJavaScript(f"addMarkers('metroR', {json.dumps(r)})")
            if self.settings['metroO']: self.web.page().runJavaScript(f"addMarkers('metroO', {json.dumps(o)})")
            if self.settings['lrt']: self.web.page().runJavaScript(f"addMarkers('lrt', {json.dumps(c)})")

    def update_search(self, text):
        text = text.strip().lower(); self.search_results.clear(); self.clear_btn.setVisible(bool(text))
        if not text: self.search_results.hide(); return
        matches = []
        for cat, items in self.data.items():
            if (cat=='bus' and not self.settings['bus']) or (cat=='bike' and not self.settings['bike']): continue
            for item in items:
                if cat == 'metro':
                    lid = item['id'][0].upper()
                    if (lid=='R' and not self.settings['metroR']) or (lid=='O' and not self.settings['metroO']) or (lid=='C' and not self.settings['lrt']): continue
                n, i, a = (item.get('name') or item.get('name_tw', '')).lower(), str(item['id']).lower(), item.get('addr', '').lower()
                sc = 1000 if text==i or text==n else (800 if n.startswith(text) or i.startswith(text) else (500 if text in n or text in i else (300 if text in a else 0)))
                if sc > 0: matches.append((sc, cat, item))
        matches.sort(key=lambda x: x[0], reverse=True)
        if not matches: self.search_results.hide(); return
        for _, cat, item in matches[:15]:
            iw = QListWidgetItem(self.search_results); iw.setSizeHint(QSize(0, 60))
            if cat == 'bus': ic, bg, fg, sub = 'directions_bus', '#dbeafe', '#1d4ed8', f"ID: {item['id']}"
            elif cat == 'bike': ic, bg, fg, sub = 'pedal_bike', '#fef9c3', '#854d0e', item.get('addr', '')
            else:
                ic, bg, fg, sub = 'tram', '#fee2e2', '#b91c1c', f"代碼: {item['id']}"
                if item['id'].startswith('O'): bg, fg = '#ffedd5', '#c2410c'
                elif item['id'].startswith('C'): bg, fg = '#dcfce7', '#15803d'
            self.search_results.setItemWidget(iw, SearchResultItem(ic, bg, fg, item.get('name') or item.get('name_tw'), sub))
            iw.setData(Qt.ItemDataRole.UserRole, {'cat': cat, 'data': item})
        self.search_results.show(); h = min(400, self.search_results.count() * 60 + 10); self.search_results.setFixedHeight(h)

    def on_search_result_clicked(self, item):
        d = item.data(Qt.ItemDataRole.UserRole); data = d['data']
        self.open_sidebar(d['cat'], str(data['id']), data.get('name') or data.get('name_tw'), data['lat'], data['lon'], data.get('addr',''))
        self.pan_map_to_offset(data['lat'], data['lon']) 
        self.search_results.hide(); self.search_input.clear()

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            elif child.layout(): self.clear_layout(child.layout())

    def open_sidebar(self, t, i, n, la, lo, a):
        self.ctx = {'t': t, 'i': i, 'n': n}; self.sb_title.setText(n)
        
        self.clear_layout(self.sb_layout)

        if t == 'bus': self.sb_badge.setText("公車"); self.sb_badge.setStyleSheet("background-color: #dbeafe; color: #1d4ed8; border-radius: 6px; padding: 2px 8px; font-weight: bold;")
        elif t == 'bike': self.sb_badge.setText("YouBike 2.0"); self.sb_badge.setStyleSheet("background-color: #fef9c3; color: #854d0e; border-radius: 6px; padding: 2px 8px; font-weight: bold;")
        else:
            l = i[0].upper(); self.sb_badge.setText("捷運" if l in ['R','O'] else "輕軌")
            bg, fg = ("#fee2e2", "#b91c1c") if l=='R' else (("#ffedd5", "#c2410c") if l=='O' else ("#dcfce7", "#15803d"))
            self.sb_badge.setStyleSheet(f"background-color: {bg}; color: {fg}; border-radius: 6px; padding: 2px 8px; font-weight: bold;")
        self.sb_sub.setText(f"ID: {i}" if t=='bus' else (a if t=='bike' else f"車站代碼: {i}"))
        self.sidebar.show(); self.update_layout_state(); 
        # [FIX] Added Pan Map Logic
        self.pan_map_to_offset(la, lo)
        
        self.refresh_btn.start_countdown()
        self.refresh_data(); self.timer.start(30000)

    def close_sidebar(self): 
        self.sidebar.hide(); self.update_layout_state(); 
        self.refresh_btn.stop_countdown(); self.timer.stop()

    def refresh_data(self, auto=False):
        if not hasattr(self, 'ctx'): return
        if not auto:
            self.clear_layout(self.sb_layout)
            l = QLabel("載入中..."); l.setAlignment(Qt.AlignmentFlag.AlignCenter); l.setStyleSheet("color: #94a3b8; border: none;"); self.sb_layout.addWidget(l)
            self.refresh_btn.start_countdown()
        self.worker = RealtimeFetcher(self.ctx['t'], self.ctx['i'], self.ctx['n']); self.worker.info_updated.connect(self.render_sidebar); self.worker.start()

    def render_sidebar(self, res):
        self.clear_layout(self.sb_layout)
        d = res['data']
        if d is None: self.sb_layout.addWidget(QLabel("無法連線", styleSheet="color: red; padding: 20px; border: none;")); return

        if res['type'] == 'bus':
            if not d: 
                no_bus = QFrame(); no_bus.setStyleSheet("border: 2px dashed #cbd5e1; border-radius: 12px; margin-top: 20px;")
                nl = QVBoxLayout(no_bus); nl.setContentsMargins(20,40,20,40)
                nl.addWidget(IconLabel('bus_alert', 40, "#cbd5e1"), 0, Qt.AlignmentFlag.AlignCenter)
                nl.addWidget(QLabel("無營運路線", styleSheet="color: #94a3b8; font-weight: bold; border: none;"), 0, Qt.AlignmentFlag.AlignCenter)
                self.sb_layout.addWidget(no_bus); return
            for r in d:
                card = QFrame(); card.setStyleSheet("background-color: white; border-radius: 16px; border: none;")
                card.setFixedHeight(75) 
                cl = QHBoxLayout(card); cl.setContentsMargins(16, 0, 16, 0); cl.setSpacing(10)
                left_container = QWidget(); left_layout = QVBoxLayout(left_container); left_layout.setContentsMargins(0,0,0,0); left_layout.setSpacing(4)
                nd_row = QHBoxLayout(); nd_row.setContentsMargins(0,0,0,0); nd_row.setSpacing(8)
                rn = ElidedLabel(r['name']); rn.setStyleSheet("font-size: 16px; font-weight: 900; color: #1e293b; border: none;")
                dd = QLabel(r['dir']); dd.setStyleSheet("background-color: #f1f5f9; color: #64748b; padding: 2px 8px; border-radius: 6px; font-size: 11px; border: none;")
                dd.setFixedSize(dd.sizeHint()); nd_row.addWidget(rn, 1); nd_row.addWidget(dd, 0); left_layout.addLayout(nd_row)
                st = QLabel()
                if r['susp']: st.setText("末班已過"); st.setStyleSheet("color: #94a3b8; font-weight: 500; border: none;")
                elif r['eta'] == 0: st.setText("進站中"); st.setStyleSheet("color: #dc2626; font-weight: 900; font-size: 14px; border: none;"); card.setStyleSheet("background-color: #fef2f2; border-radius: 16px; border: 1px solid #fee2e2;")
                elif r['eta']: st.setText(f"{r['eta']} 分"); st.setStyleSheet("color: #2563eb; font-weight: 900; font-size: 18px; border: none;")
                else: st.setText(r['ct'] or "未發車"); st.setStyleSheet("color: #64748b; font-weight: 500; border: none;")
                cl.addWidget(left_container, 7); cl.addWidget(st, 3, Qt.AlignmentFlag.AlignRight); self.sb_layout.addWidget(card)

        elif res['type'] == 'bike':
            grid_widget = QWidget(); gl = QGridLayout(grid_widget); gl.setSpacing(15); gl.setContentsMargins(0,0,0,0)
            def make_card(title, val, icon, theme):
                f = QFrame()
                if theme == 'yellow': style = "background-color: #fffbeb; color: #92400e;"
                elif theme == 'orange': style = "background-color: #fff7ed; color: #9a3412;"
                else: style = "background-color: #f0fdf4; color: #166534;"
                f.setStyleSheet(f"QFrame {{ {style} border-radius: 20px; border: none; }}"); f.setFixedHeight(120)
                vl = QVBoxLayout(f); vl.setContentsMargins(20, 16, 20, 16)
                t = QLabel(title); c = "#92400e" if theme=='yellow' else ("#9a3412" if theme=='orange' else "#166534")
                t.setStyleSheet(f"color: {c}; font-weight: bold; background: transparent; border: none; font-size: 13px;")
                vl.addWidget(t)
                row = QHBoxLayout()
                i = IconLabel(icon, 36, c)
                v = QLabel(str(val)); v.setStyleSheet(f"color: {c}; font-size: 40px; font-weight: 900; background: transparent; border: none;")
                row.addWidget(i, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
                row.addStretch()
                row.addWidget(v, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
                vl.addLayout(row); return f
            det = d.get('available_spaces_detail', {})
            gl.addWidget(make_card("一般車輛", det.get('yb2', 0), 'pedal_bike', 'yellow'), 0, 0)
            gl.addWidget(make_card("電輔車", det.get('eyb', 0), 'bolt', 'orange'), 0, 1)
            
            # [FIX] Separate layout logic for parking card
            park = QFrame(); park.setStyleSheet("background-color: #f0fdf4; border-radius: 20px; border: none;"); park.setFixedHeight(100)
            hl = QHBoxLayout(park); hl.setContentsMargins(24, 0, 30, 0)
            left_grp = QVBoxLayout(); left_grp.setSpacing(2); left_grp.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            pl = QLabel("可歸還空位"); pl.setStyleSheet("color: #166534; font-weight: bold; font-size: 13px; border: none;")
            pi = QLabel("P"); pi.setStyleSheet("color: #15803d; font-weight: 900; font-size: 32px; border: none;"); left_grp.addWidget(pl); left_grp.addWidget(pi)
            pv = QLabel(str(d.get('empty_spaces', 0))); pv.setStyleSheet("color: #166534; font-size: 42px; font-weight: 900; border: none;")
            hl.addLayout(left_grp); hl.addStretch(); hl.addWidget(pv)
            
            self.sb_layout.addWidget(grid_widget); self.sb_layout.addWidget(park)
            self.sb_layout.addWidget(QLabel(f"更新於 {time.strftime('%H:%M')}", styleSheet="color: #cbd5e1; font-size: 11px; margin-top: 10px; qproperty-alignment: AlignCenter; border: none;"))

        elif res['type'] == 'metro':
            if not d: self.sb_layout.addWidget(QLabel("目前無列車動態", styleSheet="color: #94a3b8; padding: 20px; qproperty-alignment: AlignCenter; border: none;")); return
            for t in d:
                row = QFrame(); row.setStyleSheet("background-color: white; border-radius: 16px; border: none;")
                row.setFixedHeight(80) 
                rl = QHBoxLayout(row); rl.setContentsMargins(16, 8, 16, 8)
                nm = QLabel(t['tripHeadSign']); nm.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b; border: none;")
                est = t['estimateTime']
                if est == 0: st = QLabel("進站中"); st.setStyleSheet("color: #dc2626; font-weight: 900; border: none;")
                elif est == 1: st = QLabel("即將到站"); st.setStyleSheet("color: #ef4444; font-weight: bold; border: none;")
                else: st = QLabel(f"{est} 分"); st.setStyleSheet("color: #2563eb; font-weight: 900; font-size: 18px; border: none;")
                rl.addWidget(nm); rl.addStretch(); rl.addWidget(st); self.sb_layout.addWidget(row)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
