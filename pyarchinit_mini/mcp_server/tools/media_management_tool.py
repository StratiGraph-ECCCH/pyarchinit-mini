"""
Media Management Tool

Provides comprehensive media file management for archaeological entities:
- Upload and store media files (images, documents, videos, 3D models)
- Associate media with entities (us, inventario, pottery, struttura, tomba, tma, ut, site)
- Get, list, update, and delete media records

Built on the plugin-schema MediaService (shared with the QGIS plugin's media_table /
media_to_entity_table / media_thumb_table).
"""

import logging
import os
import base64
import tempfile
from typing import Dict, Any
from pathlib import Path
from .base_tool import BaseTool, ToolDescription
from ...services.media_service import MediaService
from ...media_manager.media_handler import MediaHandler
from ...models.media import Media

logger = logging.getLogger(__name__)


class MediaManagementTool(BaseTool):
    """Comprehensive media file management for archaeological entities"""

    def to_tool_description(self) -> ToolDescription:
        return ToolDescription(
            name="manage_media",
            description=(
                "⚠️ REQUIRED FOR ALL MEDIA OPERATIONS - This is the ONLY correct way to upload media files. "
                "DO NOT use 'insert_data' tool for media_table - it will fail. "
                "\n\n"
                "Comprehensive media file management tool: "
                "Upload, retrieve, list, update, and delete media files (images, documents, videos, 3D models). "
                "Associate media with entities: us, inventario, pottery, struttura, tomba, tma, ut, site. "
                "Supports base64-encoded content or file paths. "
                "Automatically handles: "
                "1) File storage in permanent location (~/.pyarchinit_mini/media/) "
                "2) Unique filename generation "
                "3) Database record creation with correct paths "
                "4) Thumbnail generation for images "
                "\n\n"
                "Files are stored permanently, NOT in /tmp/ where they would be lost on reboot."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["upload", "get", "list", "update", "delete"],
                        "description": (
                            "'upload' = Store new media file, "
                            "'get' = Get media by ID, "
                            "'list' = List media for entity, "
                            "'update' = Update media description/tags, "
                            "'delete' = Delete media file and record"
                        )
                    },
                    "media_id": {
                        "type": "integer",
                        "description": "Media ID (for get, update, delete operations)"
                    },
                    "entity_type": {
                        "type": "string",
                        "enum": ["us", "inventario", "pottery", "struttura", "tomba", "tma", "ut", "site"],
                        "description": "Entity key: us, inventario, pottery, struttura, tomba, tma, ut, or site"
                    },
                    "entity_id": {
                        "type": ["string", "integer"],
                        "description": "Entity primary key (integer id, e.g. id_us, id_invmat, id_rep, id_sito)"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to media file on server (for upload)"
                    },
                    "file_content_base64": {
                        "type": "string",
                        "description": "Base64-encoded file content (alternative to file_path)"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Filename for uploaded content (required with file_content_base64)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of media file (stored as descrizione)"
                    },
                    "tags": {
                        "type": "string",
                        "description": "Comma-separated tags"
                    },
                    "delete_file": {
                        "type": "boolean",
                        "description": "Delete physical file (for delete operation)",
                        "default": True
                    }
                },
                "required": ["operation"],
            },
        )

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute media management operation"""
        try:
            operation = arguments.get("operation")

            # Create DatabaseManager from db_session
            from ...database.connection import DatabaseConnection
            from ...database.manager import DatabaseManager

            # Get engine from session
            engine = self.db_session.bind
            db_connection = DatabaseConnection(engine.url.render_as_string(hide_password=False))
            db_connection._engine = engine  # Reuse existing engine
            db_manager = DatabaseManager(db_connection)

            # Initialize media service
            media_handler = MediaHandler()
            media_service = MediaService(db_manager, media_handler)

            logger.info(f"Executing media operation: {operation}")

            if operation == "upload":
                return await self._handle_upload(media_service, arguments)
            elif operation == "get":
                return await self._handle_get(media_service, arguments)
            elif operation == "list":
                return await self._handle_list(media_service, arguments)
            elif operation == "update":
                return await self._handle_update(media_service, arguments)
            elif operation == "delete":
                return await self._handle_delete(media_service, arguments)
            else:
                return self._format_error(f"Unknown operation: {operation}")

        except Exception as e:
            logger.error(f"Media management error: {str(e)}", exc_info=True)
            return self._format_error(f"Media management failed: {str(e)}")

    async def _handle_upload(
        self,
        media_service: MediaService,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle media upload operation"""
        entity_type = arguments.get("entity_type")
        entity_id = arguments.get("entity_id")
        file_path = arguments.get("file_path")
        file_content_base64 = arguments.get("file_content_base64")
        filename = arguments.get("filename")
        description = arguments.get("description", "")
        tags = arguments.get("tags", "")

        if not entity_type or entity_id is None:
            return self._format_error("entity_type and entity_id are required for upload")

        try:
            id_entity = int(entity_id)
        except (TypeError, ValueError):
            return self._format_error(f"entity_id must be an integer, got: {entity_id!r}")

        # Handle base64 content
        temp_file = None
        try:
            if file_content_base64:
                if not filename:
                    return self._format_error("filename is required when using file_content_base64")

                # Decode base64 and save to temp file
                file_content = base64.b64decode(file_content_base64)
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=Path(filename).suffix
                )
                temp_file.write(file_content)
                temp_file.close()
                file_path = temp_file.name

            elif not file_path:
                return self._format_error("Either file_path or file_content_base64 is required")

            # Check file exists
            if not os.path.exists(file_path):
                return self._format_error(f"File not found: {file_path}")

            # Store and register media (plugin schema)
            media = media_service.add_media(
                file_path=file_path,
                entity_key=entity_type,
                id_entity=id_entity,
                descrizione=description,
                tags=tags,
            )

            return self._format_success(
                result={
                    "media_id": media.id_media,
                    "filename": media.filename,
                    "mediatype": media.mediatype,
                    "filepath": media.filepath,
                    "entity_type": entity_type,
                    "entity_id": id_entity,
                    "url": media_service.public_url(media.filepath),
                },
                message=f"Media uploaded successfully: {media.filename}"
            )

        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass

    async def _handle_get(
        self,
        media_service: MediaService,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle get media by ID operation"""
        media_id = arguments.get("media_id")

        if not media_id:
            return self._format_error("media_id is required for get operation")

        media = media_service.get_media_by_id(int(media_id))

        if not media:
            return self._format_error(f"Media not found: {media_id}")

        return self._format_success(
            result={
                "media_id": media.id_media,
                "filename": media.filename,
                "filetype": media.filetype,
                "mediatype": media.mediatype,
                "filepath": media.filepath,
                "descrizione": media.descrizione,
                "tags": media.tags,
                "url": media_service.public_url(media.filepath),
                "thumb_url": media_service.thumb_url(media.id_media),
            },
            message=f"Media retrieved: {media.filename}"
        )

    async def _handle_list(
        self,
        media_service: MediaService,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle list media for entity operation"""
        entity_type = arguments.get("entity_type")
        entity_id = arguments.get("entity_id")

        if not entity_type or entity_id is None:
            return self._format_error("entity_type and entity_id are required for list operation")

        try:
            id_entity = int(entity_id)
        except (TypeError, ValueError):
            return self._format_error(f"entity_id must be an integer, got: {entity_id!r}")

        media_list = media_service.get_media_for_entity(entity_type, id_entity)

        result = {
            "entity_type": entity_type,
            "entity_id": id_entity,
            "total_count": len(media_list),
            "media_items": [
                {
                    "id_media": media.id_media,
                    "filename": media.filename,
                    "filepath": media.filepath,
                    "mediatype": media.mediatype,
                    "descrizione": media.descrizione,
                    "tags": media.tags,
                    "url": media_service.public_url(media.filepath),
                }
                for media in media_list
            ]
        }

        return self._format_success(
            result=result,
            message=f"Found {len(media_list)} media items for {entity_type} {id_entity}"
        )

    async def _handle_update(
        self,
        media_service: MediaService,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle update media metadata operation (descrizione/tags only)"""
        media_id = arguments.get("media_id")

        if not media_id:
            return self._format_error("media_id is required for update operation")

        # Build update data - the plugin schema only exposes descrizione/tags as
        # user-editable metadata (no author/is_public/etc. anymore).
        update_data = {}
        if "description" in arguments:
            update_data["descrizione"] = arguments["description"]
        if "tags" in arguments:
            update_data["tags"] = arguments["tags"]

        if not update_data:
            return self._format_error(
                "No update data provided (only 'description' and 'tags' are supported)"
            )

        with media_service.db_manager.connection.get_session() as session:
            media = session.get(Media, int(media_id))
            if not media:
                return self._format_error(f"Media not found: {media_id}")

            for field, value in update_data.items():
                setattr(media, field, value)
            session.commit()
            session.refresh(media)

            result = {
                "media_id": media.id_media,
                "filename": media.filename,
                "descrizione": media.descrizione,
                "tags": media.tags,
                "updated_fields": list(update_data.keys()),
            }
            message = f"Media updated: {media.filename}"

        return self._format_success(result=result, message=message)

    async def _handle_delete(
        self,
        media_service: MediaService,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle delete media operation"""
        media_id = arguments.get("media_id")
        delete_file = arguments.get("delete_file", True)

        if not media_id:
            return self._format_error("media_id is required for delete operation")

        # Get media info before deletion
        media = media_service.get_media_by_id(int(media_id))
        if not media:
            return self._format_error(f"Media not found: {media_id}")

        filename = media.filename
        success = media_service.delete_media(int(media_id), delete_files=delete_file)

        if success:
            return self._format_success(
                result={
                    "media_id": media_id,
                    "filename": filename,
                    "deleted_file": delete_file
                },
                message=f"Media deleted: {filename}"
            )
        else:
            return self._format_error(f"Failed to delete media: {media_id}")
