"""Serve the private local dashboard and persist pipeline deletions."""
import html
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from datetime import datetime
from build_dashboard import render_dashboard

ROOT = Path(__file__).resolve().parent
PORT = 8770
WRITE_LOCK = Lock()

def delete_manuscript(root, title, section_name="Manuscripts"):
    pipeline = root / 'pipeline.local.md'
    dashboard = root / 'dashboard.local.html'
    source = pipeline.read_text()
    page = dashboard.read_text()
    if section_name not in ('Manuscripts', 'Projects/grants', 'Events', 'Todos'):
        raise ValueError('Select a valid pipeline section.')
    marker = f'## {section_name}\n'
    prefix, remainder = source.split(marker, 1)
    section, separator, suffix = remainder.partition('\n## ')
    rows = [line for line in section.splitlines(keepends=True)
            if line.startswith('| ') and line.split('|')[1].strip() == title]
    if len(rows) != 1:
        raise ValueError('The item changed or could not be uniquely identified. Reload and try again.')
    pattern = re.compile(r'<article\b[^>]*>.*?</article>', re.S)
    def matches(match):
        heading = re.search(r'<h3[^>]*>(.*?)</h3>', match.group(), re.S)
        section_attr = re.search(r'data-pipeline-section="([^"]+)"', match.group().split('>', 1)[0])
        card_section = html.unescape(section_attr.group(1)) if section_attr else 'Manuscripts'
        return card_section == section_name and heading and html.unescape(heading.group(1)) == title
    if not any(matches(match) for match in pattern.finditer(page)):
        raise ValueError('The dashboard does not match the tracker. No changes were saved.')
    updated_source = prefix + marker + section.replace(rows[0], '', 1) + separator + suffix
    backup = root / '.tracker-backups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True)
    (backup / 'pipeline.local.md').write_text(source)
    (backup / 'dashboard.local.html').write_text(page)
    try:
        pipeline.write_text(updated_source)
        render_dashboard(pipeline, dashboard)
    except (OSError, ValueError):
        pipeline.write_text(source)
        dashboard.write_text(page)
        raise

class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, kind='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', kind + '; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        if self.path in ('/', '/dashboard.local.html'):
            page = ROOT / 'dashboard.local.html'
            if not page.exists():
                page = ROOT / 'index.html'
            self.respond(200, page.read_text(), 'text/html')
        else:
            self.respond(404, '{}')

    def do_POST(self):
        origin = f'http://127.0.0.1:{PORT}'
        if (self.path != '/api/delete' or self.headers.get('Host') != f'127.0.0.1:{PORT}'
                or self.headers.get('Origin') != origin
                or self.headers.get('X-Tracker-Action') != 'delete'):
            self.respond(403, json.dumps({'error': 'Open the local tracker to make changes.'}))
            return
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 16384:
                raise ValueError('Invalid request size.')
            payload = json.loads(self.rfile.read(size))
            title = payload.get('title')
            if not isinstance(title, str) or not title:
                raise ValueError('Select a pipeline item to delete.')
            with WRITE_LOCK:
                delete_manuscript(ROOT, title, payload.get("section", "Manuscripts"))
            self.respond(200, '{"ok":true}')
        except (ValueError, KeyError, IndexError) as error:
            self.respond(409, json.dumps({'error': str(error)}))
        except OSError:
            self.respond(500, json.dumps({'error': 'Could not save the deletion. Check file permissions.'}))

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
