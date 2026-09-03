# 3D Builder - Technical Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Implementation Details](#implementation-details)
5. [API Reference](#api-reference)
6. [Real-time Communication](#real-time-communication)
7. [Development Guide](#development-guide)
8. [Deployment](#deployment)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The 3D Builder is a complete system for generating, visualizing, and interacting with 3D stratigraphic models in PyArchInit-Mini. It integrates multiple technologies to provide a seamless experience from data to visualization.

### Key Features

- **3D Model Generation**: Create stratigraphic models from GraphML data
- **Interactive Web Viewer**: Three.js-based 3D visualization with controls
- **Blender Integration**: Professional 3D creation via MCP protocol
- **Real-time Sync**: Server-Sent Events for live updates
- **Chronological Filtering**: BCE/CE timeline with period presets
- **Stratigraphic Analysis**: Detailed proxy information panels
- **GraphML Parsing**: Automatic extraction of stratigraphic metadata

### Technology Stack

- **Backend**: Flask, SQLAlchemy, NetworkX
- **Frontend**: JavaScript ES6+, Three.js r147, Bootstrap 5
- **3D Engine**: Blender 3.0+ with custom MCP addon
- **Communication**: TCP sockets (Blender), SSE (web viewer)
- **Database**: SQLite/PostgreSQL with stratigraphic data models

---

## Architecture

### System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Web Browser                            │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────┐│
│  │  3D Builder UI │  │ Three.js Viewer │  │ EventSource ││
│  └────────┬───────┘  └────────┬────────┘  └──────┬──────┘│
└───────────┼──────────────────┼─────────────────┼─────────┘
            │                  │                  │
            │ HTTP/REST        │ glTF/JSON       │ SSE
            │                  │                  │
┌───────────┼──────────────────┼─────────────────┼─────────┐
│           ▼                  ▼                  ▼         │
│  ┌──────────────────────────────────────────────────┐    │
│  │          Flask Application Server                 │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │    │
│  │  │  Routes  │  │ Services │  │  EventStream │   │    │
│  │  └────┬─────┘  └────┬─────┘  └──────────────┘   │    │
│  └───────┼─────────────┼────────────────────────────┘    │
│          │             │                                  │
│  ┌───────┼─────────────┼────────────────────────────┐    │
│  │       ▼             ▼                             │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │    │
│  │  │ GraphML  │  │  Proxy   │  │   Blender    │   │    │
│  │  │  Parser  │  │Generator │  │   Client     │   │    │
│  │  └──────────┘  └──────────┘  └──────┬───────┘   │    │
│  │                                      │           │    │
│  └──────────────────────────────────────┼───────────┘    │
│                                         │                │
│  ┌──────────────────────────────────────┼───────────┐    │
│  │         Database Layer               │           │    │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌────┴────┐      │    │
│  │  │  US  │  │ Site │  │Period│  │Extended │      │    │
│  │  │      │  │      │  │      │  │ Matrix  │      │    │
│  │  └──────┘  └──────┘  └──────┘  └─────────┘      │    │
│  └──────────────────────────────────────────────────┘    │
└───────────────────────────────────────┼──────────────────┘
                                        │ TCP Socket
                                        │ (port 9876)
┌───────────────────────────────────────┼──────────────────┐
│                                       ▼                   │
│  ┌──────────────────────────────────────────────────┐    │
│  │              Blender 3.0+                         │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │    │
│  │  │   MCP    │  │ Command  │  │     3D       │   │    │
│  │  │  Addon   │  │ Handlers │  │    Scene     │   │    │
│  │  └──────────┘  └──────────┘  └──────────────┘   │    │
│  └──────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Input**: Web UI → Claude prompt or GraphML selection
2. **Processing**: Flask routes → GraphML Parser → Proxy Generator
3. **3D Generation**: Proxy Generator → Blender Client → Blender MCP Addon
4. **Visualization**: Blender → glTF Export → Three.js Viewer
5. **Real-time Updates**: Blender → Event Stream → SSE → Web UI

---

## Components

### Backend Components

#### 1. GraphML Parser (`pyarchinit_mini/mcp_server/graphml_parser.py`)

Parses GraphML files and combines with database US records.

**Key Methods**:
```python
load_graphml(filepath: str) -> bool
parse_node(node_id: str) -> Dict[str, Any]
get_us_data_with_graphml(us_id: int) -> Dict[str, Any]
get_relationships_for_us(us_id: int) -> Dict[str, List[int]]
get_topological_order() -> List[int]
```

**Features**:
- NetworkX graph processing
- US metadata extraction
- Stratigraphic relationship parsing
- Periodization integration
- Topological sorting for layer ordering

#### 2. Proxy Generator (`pyarchinit_mini/mcp_server/proxy_generator.py`)

Generates 3D proxy objects from stratigraphic data.

**Key Methods**:
```python
generate_proxies(graphml_file: str, options: Dict) -> List[Dict]
calculate_proxy_geometry(us_data: Dict) -> Tuple[location, scale, rotation]
assign_material_by_period(period: str) -> Dict[str, Any]
```

**Features**:
- Automatic positioning based on stratigraphic order
- Period-based material assignment
- Scale calculation from physical dimensions
- Collection/layer organization

#### 3. Blender Client (`pyarchinit_mini/mcp_server/blender_client.py`)

TCP socket client for communicating with Blender.

**Key Methods**:
```python
connect() -> bool
send_command(command_type: str, params: Dict) -> BlenderResponse
create_proxy(proxy_id, location, scale, rotation, geometry)
apply_material(proxy_id, material_name, base_color, roughness, metallic)
export_gltf(output_path, selected_only)
```

**Features**:
- Connection pooling with retries
- JSON-based protocol
- Context manager support
- High-level command wrappers
- Error handling and logging

#### 4. Event Stream (`pyarchinit_mini/mcp_server/event_stream.py`)

Server-Sent Events system for real-time updates.

**Key Classes**:
```python
class BlenderEvent:
    event_type: str
    session_id: str
    data: Dict[str, Any]
    timestamp: str

class EventStream:
    add_client(session_id: Optional[str]) -> str
    broadcast_event(event: BlenderEvent)
    stream_events(client_id: str) -> Generator[str, None, None]
```

**Event Types**:
- `proxy_created`: New proxy added
- `proxy_updated`: Proxy properties changed
- `visibility_changed`: Show/hide state changed
- `transparency_changed`: Alpha value changed
- `material_applied`: Material/color changed
- `scene_cleared`: All objects removed
- `export_complete`: glTF export finished
- `batch_complete`: Batch operation done
- `error`: Error occurred

#### 5. Flask Routes (`pyarchinit_mini/web_interface/three_d_builder_routes.py`)

API endpoints for 3D Builder functionality.

**Endpoints**:
```
GET  /3d-builder/                    - Main UI page
POST /api/3d-builder/generate       - Generate 3D model
GET  /api/3d-builder/session/{id}   - Get session proxies
GET  /api/3d-builder/events          - SSE event stream
GET  /api/3d-builder/events/stats   - Stream statistics
GET  /api/3d-builder/blender/test-connection - Test Blender
```

### Frontend Components

#### 1. UI Template (`templates/3d_builder/index.html`)

Complete web interface with multiple sections.

**Sections**:
- Prompt input for Claude-based generation
- GraphML file selector
- 3D viewer container (Three.js)
- Filter controls (period, date range, transparency)
- Proxy info panel (4 tabs)
- Active sessions list

**Interactive Elements**:
- Period presets (Bronze Age, Iron Age, Roman, Medieval)
- Date range spinboxes with sliders (-5000 to +2000)
- Transparency slider
- Show/hide toggles

#### 2. Three.js Viewer (`static/js/three-d-viewer.js`)

3D visualization engine using Three.js r147.

**Key Features**:
- GLTFLoader for model loading
- OrbitControls for camera manipulation
- Raycaster for object selection
- Dynamic material updates
- Grid and axes helpers
- Responsive canvas resizing

**Methods**:
```javascript
loadProxies(proxies: Array) - Load proxy geometries
updateProxyVisibility(us_id, visible) - Show/hide
updateProxyTransparency(us_id, alpha) - Set opacity
selectProxy(us_id) - Highlight and show info
clearScene() - Remove all objects
```

#### 3. EventSource Client

Real-time event listener in `index.html`.

**Features**:
- Automatic connection on session creation
- Event-specific handlers
- Automatic reconnection (5s timeout)
- Proper cleanup on page unload
- Session filtering support

### Blender Addon

#### PyArchInit MCP Addon (`blender_addon/pyarchinit_mcp/__init__.py`)

Complete Blender addon with socket server.

**Components**:
- `MCPSocketServer`: TCP server (port 9876)
- Command handlers for all operations
- UI panel in 3D View sidebar
- Operators for start/stop server

**Command Handlers**:
- `handle_create_proxy()`: Create mesh objects
- `handle_apply_material()`: Principled BSDF materials
- `handle_set_visibility()`: Hide/show in viewport/render
- `handle_set_transparency()`: Material alpha blending
- `handle_assign_to_collection()`: Layer management
- `handle_export_gltf()`: Export to web format
- `handle_get_scene_info()`: Query scene state
- `handle_clear_scene()`: Delete all objects
- `handle_batch_create_proxies()`: Batch operations

---

## Implementation Details

### GraphML to 3D Workflow

1. **Parse GraphML**:
   ```python
   parser = GraphMLParser(db_session)
   parser.load_graphml('/path/to/matrix.graphml')
   nodes = parser.parse_all_nodes()
   ```

2. **Extract US Data**:
   ```python
   for node in nodes:
       us_data = parser.get_us_data_with_graphml(node['us_id'])
       # Contains: stratigraphic_data, chronology, relationships
   ```

3. **Generate Proxies**:
   ```python
   generator = ProxyGenerator()
   proxies = generator.generate_proxies(nodes, options)
   # Calculates: location, scale, rotation, material
   ```

4. **Send to Blender**:
   ```python
   with BlenderClient() as client:
       for proxy in proxies:
           client.create_proxy(**proxy)
           client.apply_material(proxy['us_id'], material_data)
   ```

5. **Export glTF**:
   ```python
   client.export_gltf('/output/model.gltf')
   ```

6. **Load in Viewer**:
   ```javascript
   viewer3D.loadProxies(proxies);
   ```

### Real-time Event Flow

1. **Blender performs action** (e.g., proxy created)
2. **Command handler emits event**:
   ```python
   from pyarchinit_mini.mcp_server.event_stream import emit_proxy_created
   emit_proxy_created(session_id, proxy_data)
   ```

3. **Event stream broadcasts** to all connected clients
4. **SSE delivers to browser**:
   ```
   event: proxy_created
   data: {"event_type":"proxy_created","session_id":"abc123","data":{...}}
   ```

5. **EventSource client receives**:
   ```javascript
   eventSource.addEventListener('proxy_created', function(e) {
       const data = JSON.parse(e.data);
       viewer3D.loadProxies([data.data.proxy_data]);
   });
   ```

6. **3D viewer updates** in real-time

### Chronological Filtering

Period presets and date ranges filter visible proxies:

```javascript
// User selects "Bronze Age" preset
dateStartInput.value = -3300;  // 3300 BCE
dateEndInput.value = -1200;    // 1200 BCE

// Apply filter
currentProxies.forEach(proxy => {
    const dating_start = proxy.chronology?.dating_start;
    const dating_end = proxy.chronology?.dating_end;

    // Check if proxy overlaps with selected range
    if (dating_start >= -3300 && dating_end <= -1200) {
        viewer3D.updateProxyVisibility(proxy.us_id, true);
    } else {
        viewer3D.updateProxyVisibility(proxy.us_id, false);
    }
});
```

### Proxy Info Panel

When user clicks a proxy in 3D viewer:

1. **Three.js detects click** via Raycaster
2. **onProxySelect callback** triggered
3. **showProxyInfoPanel(proxy)** populates data
4. **4 tabs displayed**:
   - **Basic**: US type, definition, formation, interpretation
   - **Stratigraphy**: Physical characteristics, dimensions
   - **Chronology**: Period, phase, dating range (BCE/CE)
   - **Relationships**: Covers, fills, cuts (with badges)

---

## API Reference

### REST API

#### POST /api/3d-builder/generate

Generate 3D model from GraphML and US data.

**Request**:
```json
{
  "graphml_file_id": 123,
  "site_id": 1,
  "options": {
    "include_periods": ["Bronze Age", "Iron Age"],
    "export_format": "gltf"
  }
}
```

**Response**:
```json
{
  "success": true,
  "session_id": "abc123def456",
  "proxies_count": 42,
  "message": "3D model generated successfully"
}
```

#### GET /api/3d-builder/session/{session_id}

Get all proxies for a session.

**Response**:
```json
{
  "success": true,
  "session_id": "abc123def456",
  "proxies": [
    {
      "us_id": 1,
      "stratigraphic_data": {
        "sito": "Site 1",
        "area": "A",
        "us": 1,
        "definizione_stratigrafica": "Layer",
        "interpretazione": "Living floor",
        ...
      },
      "chronology": {
        "period_name": "Bronze Age",
        "dating_start": -1200,
        "dating_end": -800,
        ...
      },
      "relationships": {
        "covers": [2, 3],
        "covered_by": [],
        "fills": [],
        ...
      },
      "geometry": {
        "location": [0, 0, 0],
        "scale": [5, 5, 1],
        "rotation": [0, 0, 0]
      }
    }
  ]
}
```

### Server-Sent Events API

#### GET /api/3d-builder/events?session_id={id}

Real-time event stream for 3D updates.

**Event Format**:
```
event: proxy_created
data: {"event_type":"proxy_created","session_id":"abc123","data":{"proxy_data":{...}},"timestamp":"2025-11-01T12:00:00"}

event: visibility_changed
data: {"event_type":"visibility_changed","session_id":"abc123","data":{"proxy_id":"US_1","visible":false},"timestamp":"2025-11-01T12:01:00"}
```

**Client Code**:
```javascript
const eventSource = new EventSource('/api/3d-builder/events?session_id=abc123');

eventSource.addEventListener('proxy_created', (e) => {
    const event = JSON.parse(e.data);
    console.log('New proxy:', event.data.proxy_data);
});

eventSource.onerror = (error) => {
    console.error('SSE error:', error);
    eventSource.close();
};
```

### Blender MCP Protocol

#### JSON Command Format

**Request**:
```json
{
  "type": "create_proxy",
  "params": {
    "proxy_id": "US_1",
    "location": {"x": 0, "y": 0, "z": 0},
    "scale": {"x": 5, "y": 5, "z": 1},
    "rotation": {"x": 0, "y": 0, "z": 0},
    "geometry": "CUBE"
  }
}
```

**Response**:
```json
{
  "status": "success",
  "result": {
    "proxy_id": "US_1",
    "object_name": "Proxy_US_1"
  },
  "message": "Created proxy US_1"
}
```

---

## Development Guide

### Setting Up Development Environment

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Database**:
   ```bash
   export DATABASE_URL="sqlite:///data/pyarchinit_tutorial.db"
   ```

3. **Start Flask Server**:
   ```bash
   python -m pyarchinit_mini.web_interface.app
   ```

4. **Install Blender Addon** (optional):
   ```bash
   cp -r blender_addon/pyarchinit_mcp ~/.config/blender/3.x/scripts/addons/
   # Enable in Blender: Edit → Preferences → Add-ons → PyArchInit MCP
   ```

### Adding New Event Types

1. **Define event in `event_stream.py`**:
   ```python
   def emit_custom_event(session_id: str, data: Dict[str, Any]):
       event = BlenderEvent(
           event_type='custom_event',
           session_id=session_id,
           data=data
       )
       get_event_stream().broadcast_event(event)
   ```

2. **Add handler in frontend**:
   ```javascript
   eventSource.addEventListener('custom_event', function(e) {
       const data = JSON.parse(e.data);
       // Handle event
   });
   ```

### Extending Blender Commands

1. **Add handler in `blender_addon/__init__.py`**:
   ```python
   def handle_custom_command(params: Dict[str, Any]) -> Dict[str, Any]:
       # Implementation
       return {
           'status': 'success',
           'result': {},
           'message': 'Command executed'
       }
   ```

2. **Register in COMMAND_HANDLERS**:
   ```python
   COMMAND_HANDLERS = {
       'custom_command': handle_custom_command,
   }
   ```

3. **Add client method in `blender_client.py`**:
   ```python
   def custom_command(self, param1, param2):
       response = self.send_command('custom_command', {
           'param1': param1,
           'param2': param2
       })
       return response.result
   ```

---

## Deployment

### Production Checklist

- [ ] Set `FLASK_ENV=production`
- [ ] Use PostgreSQL instead of SQLite
- [ ] Configure WSGI server (Gunicorn/uWSGI)
- [ ] Set up reverse proxy (Nginx/Apache)
- [ ] Enable HTTPS
- [ ] Configure firewall (allow port 9876 for Blender)
- [ ] Set up Blender headless server
- [ ] Configure event stream timeout
- [ ] Enable logging and monitoring
- [ ] Set up backup system

### Environment Variables

```bash
DATABASE_URL="postgresql://user:pass@localhost/pyarchinit"
# generate one: python -c 'import secrets; print(secrets.token_urlsafe(48))'
# leave it unset and a private key is created in $PYARCHINIT_HOME/session.key
FLASK_SECRET_KEY="<48 random bytes, url-safe>"
BLENDER_HOST="localhost"
BLENDER_PORT=9876
EVENT_STREAM_TIMEOUT=30
```

---

## Troubleshooting

### Common Issues

#### Blender Connection Failed

**Symptoms**: "Connection refused" error when testing Blender

**Solutions**:
1. Check Blender is running with addon enabled
2. Verify port 9876 is open: `telnet localhost 9876`
3. Check firewall settings
4. Review Blender console for errors

#### SSE Not Working

**Symptoms**: Events not received in browser

**Solutions**:
1. Check browser console for EventSource errors
2. Verify `/api/3d-builder/events` returns 200 OK
3. Check session_id matches
4. Disable browser extensions (ad blockers)
5. Test with `curl -N http://localhost:5001/api/3d-builder/events`

#### 3D Viewer Empty

**Symptoms**: Viewer loads but shows no objects

**Solutions**:
1. Check browser console for Three.js errors
2. Verify proxies data: `/api/3d-builder/session/{id}`
3. Check glTF file is valid
4. Verify geometry calculations (scale > 0)
5. Check camera position and zoom

#### GraphML Parsing Errors

**Symptoms**: "Failed to parse GraphML" error

**Solutions**:
1. Validate GraphML XML syntax
2. Check node/edge data attributes
3. Verify US IDs exist in database
4. Check GraphML version compatibility
5. Review parser logs for details

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check event stream stats:
```bash
curl http://localhost:5001/api/3d-builder/events/stats
```

Test Blender connection:
```bash
python pyarchinit_mini/mcp_server/blender_client.py --test
```

---

## Performance Considerations

- **Event Stream**: Limit to 100 events per client queue
- **Three.js**: Use LOD for large scenes (>1000 objects)
- **SSE**: Configure nginx/apache for long-lived connections
- **Database**: Index US foreign keys and timestamps
- **Blender**: Use batch commands for multiple proxies
- **glTF**: Enable compression for large exports

---

## Security Considerations

- **Authentication**: All endpoints require login (@login_required)
- **Input Validation**: Sanitize GraphML XML and user inputs
- **File Uploads**: Restrict file types and sizes
- **SQL Injection**: Use parameterized queries (SQLAlchemy)
- **XSS**: Escape user-generated content in templates
- **CSRF**: Flask-WTF CSRF tokens enabled
- **Blender execute_python**: Disable in production or restrict access

---

## Future Enhancements

- [ ] WebGL2/WebGPU for better performance
- [ ] VR/AR support for immersive viewing
- [ ] Multi-user collaborative editing
- [ ] Real-time multiplayer synchronization
- [ ] Advanced materials (PBR, textures)
- [ ] Animation timeline for temporal visualization
- [ ] Point cloud integration
- [ ] Photogrammetry import
- [ ] Cloud rendering (AWS/GCP)
- [ ] Mobile app (React Native)

---

## License

Same as PyArchInit-Mini (GPL-3.0)

## Contributors

- PyArchInit Team
- Claude Code (AI Assistant)

## Support

- GitHub Issues: https://github.com/pyarchinit/pyarchinit-mini/issues
- Documentation: https://pyarchinit.github.io/pyarchinit-mini
- Community: PyArchInit mailing list

---

**Last Updated**: 2025-11-01
**Version**: 1.0.0
**Status**: Production Ready (pending Blender testing)
