"""Pure Bodywell creative Final name contract (Liel 2026-10-21: must match Coolina exactly).

Shared by every Bodywell task opener (board 6205503312). No credentials, no API calls.

Order (identical to coolina_initial_naming.py):
  {serial}_{v}_{Title}_{Parent}_{Funnel}_Sw{Swimlane}_{IterationType}_{Avatar}_{Angle}_
  Fmt{Format}_{AssetType}_Own{Owner}[_{AgentName}Agent{ver}]_Edt{Editor}[_{Tag}...]

Difference from Coolina at task opening: Bodywell fields are routinely blank, so opening NEVER
blocks on metadata. A missing/invalid field becomes TBD in its own segment only (exactly like
review_name). Only an invalid serial blocks. Owner is the resolved human requester, never the
technical API identity (Max Openclaw); unresolved -> OwnTBD.

Columns: Final name = long_text__1. The old formula column formula_mm14161q
("Old Final Name (Auto)") is never written.
"""
import re

BOARD_ID = '6205503312'
SERIAL_COLUMN = 'text8'
FINAL_NAME_COLUMN = 'long_text__1'
OLD_FORMULA_COLUMN = 'formula_mm14161q'  # never written
OWNER_COLUMN = 'multiple_person_mm8939bm'
EDITOR_COLUMN = 'people'
PARENT_COLUMN = 'text54'
TYPE_COLUMN = 'dropdown_mm13yrg8'
FUNNEL_COLUMN = 'status0__1'
SWIMLANE_COLUMN = 'color_mm2ddq16'
ITERATION_COLUMN = 'status_14__1'
AVATAR_COLUMN = 'dropdown_mm14a64e'  # Micro Persona
ANGLE_COLUMN = 'text_mkq79zpa'
FORMAT_COLUMN = 'dropdown_mm2d8e9p'
ASSET_COLUMN = 'status_16__1'  # Creative Type
AI_AGENT_COLUMN = 'color_mm4hky6c'
# Tags column is being added to the board (2026-10-21); resolve it from the live schema at runtime.
TAGS_COLUMN = None

# Monday user id of the technical API identity. Never a business Owner.
TECHNICAL_USER_IDS = frozenset({102108402})
TECHNICAL_NAMES = frozenset({'maxopenclaw', 'max', 'automation', 'tbd'})

ASSET_TYPES = {'vid': 'Video', 'video': 'Video', 'img': 'Image', 'image': 'Image',
               'carousel': 'Carousel', 'gif': 'GIF', 'copy': 'Copy'}
AGENT_LABEL_RE = re.compile(r'^(.+?)(?: ([0-9.]+))?$')
SERIAL_RE = re.compile(r'BW[0-9]+')
PARENT_RE = re.compile(r'P?BW([0-9]+)(?:_?V([0-9]+))?', re.I)

READBACK_IDS = [SERIAL_COLUMN, FINAL_NAME_COLUMN, OWNER_COLUMN, EDITOR_COLUMN, PARENT_COLUMN,
                TYPE_COLUMN, FUNNEL_COLUMN, SWIMLANE_COLUMN, ITERATION_COLUMN, AVATAR_COLUMN,
                ANGLE_COLUMN, FORMAT_COLUMN, ASSET_COLUMN, AI_AGENT_COLUMN]


def compact(value):
    return re.sub(r'[^\w]', '', str(value if value is not None else '')).replace('_', '')


def _values(value):
    """Normalise a label/people value to a list of non-empty strings ('A, B' -> ['A','B'])."""
    if value is None:
        return []
    raw = [value] if isinstance(value, str) else list(value)
    out = []
    for item in raw:
        for part in str(item if item is not None else '').split(','):
            if part.strip():
                out.append(part.strip())
    return out


def _single(value):
    vals = _values(value)
    return vals[0] if len(vals) == 1 else ''


def agent_token(label):
    """'Cody 2.2' -> 'CodyAgent2.2', 'BioCard Pro' -> 'BioCardProAgent', blank -> ''."""
    text = str(label or '').strip()
    if not text:
        return ''
    match = AGENT_LABEL_RE.fullmatch(text)
    if match is None:
        return ''
    name = compact(match.group(1))
    if not name:
        return ''
    return name + 'Agent' + (match.group(2) or '')


def tag_tokens(tags):
    """Compacted, de-duplicated (case-insensitive), sorted tag tokens. Same as Coolina."""
    if tags is None:
        return []
    raw = [tags] if isinstance(tags, str) else list(tags)
    out = []
    for item in raw:
        if not isinstance(item, str):
            raise ValueError('Tags must be tag names (text)')
        for part in item.split(','):
            token = compact(part)
            if token and token.casefold() not in [t.casefold() for t in out]:
                out.append(token)
    return sorted(out, key=lambda t: (t.casefold(), t))


def valid_serial(serial):
    return isinstance(serial, str) and SERIAL_RE.fullmatch(serial) is not None


def version(serial, existing_final_name=''):
    """Keep {serial}_v#_ from the current Final name; otherwise v1. Never Total Versions."""
    match = re.match(re.escape(str(serial)) + r'_(v[1-9][0-9]*)_', str(existing_final_name or ''), re.I)
    return match.group(1).lower() if match else 'v1'


def _title(serial, title):
    text = str(title or '').strip()
    prefix = re.escape(serial) if serial else r'BW[0-9]+'  # preview: serial not yet assigned
    return compact(re.sub(r'^' + prefix + r'\s*[—–-]\s*', '', text))


def _parent(serial, parent, typ):
    text = str(parent or '').strip()
    if not text:
        return 'Pnone' if _single(typ) == 'New' else 'PTBD'
    if text.casefold() == 'pnone':
        return 'Pnone'
    match = PARENT_RE.fullmatch(text)
    if not match:
        return 'PTBD'
    if serial and 'BW' + match.group(1) == serial:
        return 'PTBD'
    return 'PBW' + match.group(1) + ('V' + match.group(2) if match.group(2) else '')


def _human(name):
    token = compact(name)
    return '' if not token or token.casefold() in TECHNICAL_NAMES else token


def _segments(serial, ver, cfg):
    """Return (parts, missing) for one Bodywell name. Never raises on metadata."""
    missing = []

    def need(token, label, prefix=''):
        if not token or token.upper() == 'TBD':
            missing.append(label)
            return prefix + 'TBD'
        return prefix + token

    title = need(_title(serial, cfg.get('title')), 'Item name')
    parent = _parent(serial, cfg.get('parent'), cfg.get('type'))
    if parent == 'PTBD':
        missing.append('Parent SN')
    funnel = compact(cfg.get('funnel'))
    if len(funnel) > 1 and funnel[0] in 'Ff':
        funnel = funnel[1:]
    funnel = need(funnel, 'Funnel Status')
    swim = compact(cfg.get('swimlane'))
    swimlane = need(swim.title() if swim.upper() != 'TBD' else '', 'Swimlane', 'Sw')
    iteration = need(compact(_single(cfg.get('iteration_type'))), 'Iteration Type')
    avatar = need(compact(_single(cfg.get('avatar'))), 'Micro Persona')
    angle = need(compact(cfg.get('angle')), 'Angle')
    fmt = need(compact(_single(cfg.get('format'))), 'Format', 'Fmt')
    asset = need(ASSET_TYPES.get(str(cfg.get('asset_type') or '').strip().casefold(), ''), 'Creative Type')
    owners = _values(cfg.get('owner_names'))
    owner = need(_human(owners[0]) if len(owners) == 1 else '', 'Owner', 'Own')
    parts = [serial, ver, title, parent, funnel, swimlane, iteration, avatar, angle, fmt, asset, owner]
    agent = agent_token(cfg.get('ai_agent'))
    if agent:
        parts.append(agent)
    editors = [compact(e) for e in _values(cfg.get('editor_names')) if compact(e)]
    parts.append('Edt' + ('+'.join(editors) if editors else 'TBD'))  # blank editor is normal at opening
    parts.extend(tag_tokens(cfg.get('tags')))
    return parts, missing


def build(serial, cfg):
    """Initial Final name for a Bodywell task. Only an invalid serial blocks."""
    if not valid_serial(serial):
        raise ValueError('A valid Bodywell creative serial (BW digits) is required')
    parts, _ = _segments(serial, version(serial, cfg.get('existing_final_name')), cfg)
    return '_'.join(parts)


def missing_fields(cfg, serial=''):
    return _segments(serial or 'BW0', 'v1', cfg)[1]


def preview(cfg):
    """Pre-creation preview; the real serial is assigned by Monday after create_item."""
    parts, _ = _segments('', 'v1', cfg)
    parts[0] = '{serial}'
    return '_'.join(parts)


def cfg_from_columns(item_name, rows, tags_column=None):
    """Build a naming cfg from Monday column texts {column_id: text | {'text':...}}."""
    def text(cid):
        value = rows.get(cid) if cid else None
        if isinstance(value, dict):
            value = value.get('text')
        return value if value is not None else ''
    return {'title': item_name, 'parent': text(PARENT_COLUMN), 'type': text(TYPE_COLUMN),
            'funnel': text(FUNNEL_COLUMN), 'swimlane': text(SWIMLANE_COLUMN),
            'iteration_type': text(ITERATION_COLUMN), 'avatar': text(AVATAR_COLUMN),
            'angle': text(ANGLE_COLUMN), 'format': text(FORMAT_COLUMN),
            'asset_type': text(ASSET_COLUMN), 'owner_names': text(OWNER_COLUMN),
            'ai_agent': text(AI_AGENT_COLUMN), 'editor_names': text(EDITOR_COLUMN),
            'tags': text(tags_column) if tags_column else [],
            'existing_final_name': text(FINAL_NAME_COLUMN)}


def find_tags_column(schema):
    """Return the live board Tags column id, or None while it does not exist yet."""
    for column in schema or []:
        if column.get('type') in ('tags', 'tag'):
            return column['id']
    return None


def valid_owner_id(owner_id):
    try:
        value = int(owner_id)
    except (TypeError, ValueError):
        return None
    return value if value > 0 and value not in TECHNICAL_USER_IDS else None


def naming_columns(cfg, serial=None):
    """Column values to write for a new task.

    Owner (resolved human only) belongs in the create_item column_values. The Final name is
    added when the Monday serial is known (Monday assigns text8 after creation).
    """
    columns = {}
    owner = valid_owner_id(cfg.get('owner_id'))
    if owner:
        columns[OWNER_COLUMN] = {'personsAndTeams': [{'id': owner, 'kind': 'person'}]}
    if serial is not None:
        columns[FINAL_NAME_COLUMN] = {'text': build(serial, cfg)}
    return columns


# --- Edit - Review rename mirror (native Code step built from the same SPEC) ------------------
# Input keys follow Monday's native naming of the board columns (title -> item_<title>_<kind>_1).
REVIEW_KEYS = {
    'serial': 'item_serial_number_1', 'final_name': 'item_final_name_1', 'title': 'item_name_1',
    'parent': 'item_parent_sn_1', 'type': 'item_type_labels_1',
    'funnel': 'item_funnel_status_label_1', 'swimlane': 'item_swimlane_label_1',
    'iteration_type': 'item_iteration_type_label_1', 'avatar': 'item_micro_persona_labels_1',
    'angle': 'item_angle_1', 'format': 'item_format_labels_1',
    'asset_type': 'item_creative_type_label_1', 'owner_names': 'item_owner_names_1',
    'ai_agent': 'item_ai_agent_label_1', 'editor_names': 'item_editor_names_1',
    'tags': 'item_tags_labels_1',
}


def review_name(item, keys=None):
    """Return {'name','missing','note','post_update'} for an Edit - Review rename."""
    keys = dict(REVIEW_KEYS, **(keys or {}))
    get = lambda field: item.get(keys[field])  # noqa: E731
    serial = _single(get('serial'))
    if not valid_serial(serial):
        raise ValueError('A valid Bodywell creative serial (BW digits) is required')
    old_name = _single(get('final_name')) if not isinstance(get('final_name'), str) else get('final_name').strip()
    cfg = {field: get(field) for field in REVIEW_KEYS if field not in ('serial', 'final_name')}
    if isinstance(cfg.get('title'), list):
        cfg['title'] = _single(cfg['title'])
    if isinstance(cfg.get('angle'), list):
        cfg['angle'] = _single(cfg['angle'])
    if isinstance(cfg.get('parent'), list):
        cfg['parent'] = _single(cfg['parent'])
    parts, missing = _segments(serial, version(serial, old_name), cfg)
    name = '_'.join(parts)
    note = ('Final name has TBD for: ' + ', '.join(missing) + '. Owner: please fill in these fields, '
            'then move this task back to Edit - Review to refresh the Final name.') if missing else ''
    return {'name': name, 'missing': missing, 'note': note, 'post_update': bool(missing) and name != old_name}
