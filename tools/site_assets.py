"""Shared, self-contained assets for online and offline reading pages."""
from urllib.parse import quote

_ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
         '<rect width="32" height="32" rx="7" fill="#225a43"/>'
         '<path d="M6 8c4-1 7 0 10 2 3-2 6-3 10-2v16c-4-1-7 0-10 2-3-2-6-3-10-2z" '
         'fill="none" stroke="white" stroke-width="2" stroke-linejoin="round"/>'
         '<path d="M16 10v16" stroke="white" stroke-width="2"/></svg>')
FAVICON = '<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,' + quote(_ICON, safe='') + '">'
