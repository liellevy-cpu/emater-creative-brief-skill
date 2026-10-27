"""Pure Coolina video naming contract approved by Liel 2026-10-11.

No credentials, API calls, profile identities, hook-count versions or publishing.
Board label IDs below were checked against the same-day authenticated schema
snapshot naming-repair-co8865/full_schema.json; schema drift must fail closed.
"""
import json
import re

# 2026-10-18 (Liel): Format is the one canonical format column. The old Primary Format
# column (dropdown_mm721msd) is retired (2026-10-19); the name below is kept only as an
# alias for Format so older callers keep working. Never write dropdown_mm721msd.
FORMAT_COLUMN = 'dropdown_mm14rmx0'
PRIMARY_FORMAT_COLUMN = FORMAT_COLUMN
ITERATION_COLUMN = 'dropdown_mkskhreg'
FINAL_NAME_COLUMN = 'long_text_mkrxjtnx'
OWNER_COLUMN = 'multiple_person_mkscqwjv'
EDITOR_COLUMN = 'multiple_person_mkrwpfa6'
# Tags (Liel 2026-10-21): board Tags column. Tags are optional; only tagged tasks get them
# appended at the very end of the name (..._EdtName_SimonP4). Untagged names are unchanged.
TAGS_COLUMN = 'tag_mm8bzts'
# Core labels (Liel 2026-10-23, DESIGN: ~/.hermes/work/coolina-message-labels/DESIGN.md).
# Filled by the central Henry labeler AFTER the task opens; agents never write or require them.
CORE_PROFILE_COLUMN = 'dropdown_mm8dgmyq'   # 'P1 · The man who already wants it'
CORE_ANGLE_COLUMN = 'dropdown_mm8d8rvj'     # 'P1-A1 · Owners go out of their way to get it'
CORE_MESSAGE_COLUMN = 'dropdown_mm8d1jw3'   # 'P1-M1b · He loved his knife ...'
# Old Avatar / Angle columns are retired (2026-10-23): never write, read back or require them.
RETIRED_AVATAR_COLUMN = 'dropdown_mm14xwvn'
RETIRED_ANGLE_COLUMN = 'dropdown_mm14etc4'
RETIRED_COLUMNS = (RETIRED_AVATAR_COLUMN, RETIRED_ANGLE_COLUMN)
FORMATS = ('AI Voiceover', 'Face-to-camera', 'POV — Warehouse/Employee',
           'POV — Store', 'POV — Customer/Home', 'Skit/Conversation', 'Song/Music-led')
ITERATIONS = ('NewOffer', 'TMP', 'NetNew', 'Optimization', 'HookReplacement',
              'New Size / Placement', 'Hook Stack', 'Lead Swap', 'Body Swap',
              'Format Swap', 'Media Scale', 'Angle Swap', 'Knife swap',
              'Language swap', 'Hook Swap', 'Re-edit', 'New Video',
              'Body Improvement', 'Mixing Task')
FUNNEL_LABELS = {'2NEW':'2NEW','BIS':'BIS','BACK IN STOCK':'BIS','BBQ':'BBQ',
                 'BEAST':'BEAST','MYSTERY BUNDLE':'Mystery Bundle','HOLIDAY':'Holiday',
                 'NEW ARRIVALS':'New Arrivals','UNIQUE':'Unique'}
AGENTS = ('Ivan', 'Isaac', 'Camilla', 'Sam', 'Gina', 'Cole')
# AI Agent label may carry a release. Template {Name}Agent{version}: 'Cole 2.0' -> 'ColeAgent2.0', 'Camilla' -> 'CamillaAgent' (Liel 2026-10-15).
AGENT_LABEL_RE = re.compile(r'(' + '|'.join(AGENTS) + r')(?: ([0-9]+(?:\.[0-9]+)*))?')

def agent_token(label):
    match = AGENT_LABEL_RE.fullmatch(str(label or '').strip())
    if not match:
        raise ValueError('AI Agent must be an approved business agent, never a technical identity')
    return match.group(1) + 'Agent' + (match.group(2) or '')

def compact(value):
    return re.sub(r'[^\w]', '', str(value)).replace('_', '')

def tag_tokens(tags):
    """Name tokens for tags: compacted, de-duplicated (case-insensitive), sorted.

    Must stay identical to the live Review - Editing Code step (workflow 18434960853).
    Accepts a list of names or one comma-separated string; blank means no tags.
    """
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

# Name tokens: profile 'P1 · ...' -> P1; angle 'P1-A1 · ...' -> A1; message 'P1-M1b · ...' -> M1b.
# Anything blank, multi-valued, TBD or unrecognised -> TBD (its own positional segment).
# Must stay identical to the native Review - Editing code (tests/evidence/core-labels/native_core.txt).
_CORE_RULES = ((r'P([0-9]+)', 'P'), (r'(?:P[0-9]+-)?A([0-9]+)', 'A'), (r'(?:P[0-9]+-)?M([0-9]+[a-z]*)', 'M'))

def _core_token(label, pattern, letter):
    code = (label if isinstance(label, str) else '').split('\u00b7')[0].strip()
    found = re.fullmatch(pattern, code)
    return letter + found.group(1) if found else 'TBD'

def core_tokens(profile_label, angle_label, message_label):
    """Pure: Core Profile/Angle/Message label text (or bare code) -> [profile, angle, message] tokens."""
    return [_core_token(v, *rule) for v, rule in zip((profile_label, angle_label, message_label), _CORE_RULES)]

def required(cfg, key):
    value = cfg.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Missing single required naming field: '+key)
    return value.strip()

def validate(cfg):
    if str(cfg.get('brand') or 'Coolina').casefold() != 'coolina' or cfg.get('asset_type', 'Video') != 'Video':
        raise ValueError('This naming contract supports Coolina video only')
    # Avatar/Angle retired 2026-10-23: no longer required; tolerated and ignored if a caller still passes them.
    for key in ('concept_name','creative_funnel','swimlane','iteration_type','format','requester_monday_name','parent_serial'):
        if not compact(required(cfg,key)):
            raise ValueError('Empty naming segment: '+key)
    parent = required(cfg,'parent_serial')
    if parent != 'Pnone' and not re.fullmatch(r'PCO[0-9]+',parent):
        raise ValueError('Parent must explicitly be Pnone or PCO followed by digits')
    if cfg['format'] not in FORMATS:
        raise ValueError('Primary Format must be exactly one approved board coverage label')
    if cfg['iteration_type'] not in ITERATIONS:
        raise ValueError('Iteration Type must be exactly one active board label')
    if cfg['swimlane'] not in ('NEW','IMPROVE','EXPAND','REFRESH') or cfg['creative_funnel'].upper() not in FUNNEL_LABELS:
        raise ValueError('Invalid Funnel or Swimlane label')
    human = compact(cfg['requester_monday_name'])
    if human.casefold() in ('maxopenclaw','max','automation','tbd'):
        raise ValueError('Owner must be a resolved human, not a technical identity')
    requester = cfg.get('requester_monday_user_id')
    if not requester or int(requester) <= 0 or int(cfg.get('owner_id') or requester) != int(requester):
        raise ValueError('Owner ID must match the resolved accountable human requester')
    resolution = cfg.get('_requester_resolution',{})
    if resolution and not resolution.get('mapped') and not cfg.get('_explicit_requester'):
        raise ValueError('Unmapped requester cannot fall back to a different human')
    agent = str(cfg.get('_ai_agent_name') or cfg.get('ai_agent') or '').strip()
    if agent:
        agent_token(agent)
    if bool(cfg.get('editor_name')) != bool(cfg.get('editor_id')):
        raise ValueError('Named editor needs a matching resolved editor ID')
    for key in ('core_profile','core_angle','core_message'):
        if cfg.get(key) is not None and not isinstance(cfg.get(key), str):
            raise ValueError(key+' must be label text or a short code')
    tags = cfg.get('tags')
    if tags is not None and not isinstance(tags, (list, tuple)):
        raise ValueError('tags must be a list of tag names')
    for tag in tags or []:
        if not isinstance(tag, str) or not tag.strip() or compact(tag) != tag.strip():
            raise ValueError('Each tag must be an exact Monday tag name without spaces or symbols: '+repr(tag))
    return cfg

def version(serial,cfg):
    # New task, including an iteration with its own serial, always begins v1.
    if not cfg.get('item_id'):
        return 'v1'
    old = str(cfg.get('existing_final_name') or '')
    match = re.match(re.escape(serial)+r'_(v[1-9][0-9]*)_',old,re.I)
    if not match:
        raise ValueError('Existing output version must be read before renaming; never infer it from Total Versions')
    return match.group(1).lower()

def build(serial,cfg):
    validate(cfg)
    if not re.fullmatch(r'CO[0-9]+',str(serial)):
        raise ValueError('A valid Coolina creative serial is required')
    if cfg['parent_serial'] == 'P'+serial:
        raise ValueError('Creative cannot be its own parent')
    title=re.sub(r'^'+re.escape(serial)+r'\s*[—–-]\s*','',cfg['concept_name']).strip()
    parts=[serial,version(serial,cfg),compact(title),cfg['parent_serial'],
           compact(FUNNEL_LABELS[cfg['creative_funnel'].upper()]),'Sw'+cfg['swimlane'].title(),
           compact(cfg['iteration_type']),
           *core_tokens(cfg.get('core_profile'),cfg.get('core_angle'),cfg.get('core_message')),
           'Fmt'+compact(cfg['format']),'Video','Own'+compact(cfg['requester_monday_name'])]
    agent=str(cfg.get('_ai_agent_name') or cfg.get('ai_agent') or '').strip()
    if agent:parts.append(agent_token(agent))
    parts.append('Edt'+(compact(cfg.get('editor_name') or '') or 'TBD'))
    parts.extend(tag_tokens(cfg.get('tags')))
    if any(not part for part in parts):raise ValueError('Empty filename segment')
    return '_'.join(parts)


# --- Review - Editing rename mirror (live native Code step of workflow 18434960853) ---------------
# build()/validate() above stay STRICT for task opening (including Cole's human Format confirmation).
# review_name() mirrors the saved native code byte-for-byte in behaviour; parity is enforced by
# coolina-task-creator/tests/test_review_name_tbd.py against tests/evidence/core-labels/native_core.txt
# (2026-10-23 core labels; tags/native_tags.txt is the previous live code, kept as history).
# Missing/invalid values become TBD in their own segment only; tags (if any) go at the very end.
# Core Profile/Angle/Message TBDs are never listed in the Owner note (the labeler/Liel own them).
REVIEW_KEYS = ('item_serial_number_1','item_final_name_1','item_asset_type_label_1','item_name_1',
               'item_parent_serial_number_1','item_funnel_label_1','item_swimlane_label_1',
               'item_iteration_type_labels_1','item_core_profile_labels_1',
               'item_core_angle_labels_1','item_core_message_labels_1','item_format_labels_1','item_owner_names_1','item_ai_agent_label_1',
               'item_editor_designer_names_1','item_tags_labels_1')

def review_name(item):
    """Return {'name','missing','note','post_update'} for a Review - Editing rename."""
    missing=[]
    def values(key):
        value=item.get(key)
        if value is None:return []
        if isinstance(value,list):return [str(v).strip() for v in value if str(v).strip()]
        if not isinstance(value,str):return ['?','?']
        return [value.strip()] if value.strip() else []
    def single(key):
        v=values(key);return v[0] if len(v)==1 else ''
    def seg(key,label,prefix=''):
        token=compact(single(key))
        if not token or token.upper()=='TBD':
            missing.append(label);return prefix+'TBD'
        return prefix+token
    serial=single('item_serial_number_1')
    if not re.fullmatch(r'CO[0-9]+',serial):
        raise ValueError('A valid Coolina creative serial is required')
    old_name=single('item_final_name_1')
    found=re.match(r'^'+serial+r'_(v[1-9][0-9]*)_',old_name,re.I)
    if not found:
        raise ValueError('Output version is missing; Total Versions is not an output version')
    asset=single('item_asset_type_label_1')
    if asset and asset!='Video':
        raise ValueError('Non-video naming awaits an approved format mapping')
    title=compact(re.sub(r'^'+serial+r'\s*[—–-]\s*','',single('item_name_1')))
    if not title:
        missing.append('Item name');title='TBD'
    parent=single('item_parent_serial_number_1')
    if not (parent=='Pnone' or re.fullmatch(r'PCO[0-9]+',parent)) or parent=='P'+serial:
        missing.append('Parent Serial Number');parent='PTBD'
    funnel=seg('item_funnel_label_1','Funnel')
    swimlane=compact(single('item_swimlane_label_1'))
    if swimlane and swimlane.upper()!='TBD':swimlane='Sw'+swimlane.title()
    else:
        missing.append('Swimlane');swimlane='SwTBD'
    iteration=seg('item_iteration_type_labels_1','Iteration Type')
    core=core_tokens(single('item_core_profile_labels_1'),single('item_core_angle_labels_1'),
                     single('item_core_message_labels_1'))  # never added to `missing`
    fmt=single('item_format_labels_1')
    if fmt in FORMATS:fmt='Fmt'+compact(fmt)
    else:
        missing.append('Format');fmt='FmtTBD'
    if not asset:
        missing.append('Asset Type');asset='TBD'
    owners=values('item_owner_names_1')
    owner=compact(owners[0]) if len(owners)==1 and ',' not in owners[0] else ''
    if not owner or owner.lower() in ('maxopenclaw','tbd'):
        missing.append('Owner');owner='TBD'
    ai=''
    agent=AGENT_LABEL_RE.fullmatch(single('item_ai_agent_label_1'))
    if agent:
        ai=agent.group(1)+'Agent'+(agent.group(2) or '')
    elif values('item_ai_agent_label_1'):
        missing.append('AI Agent (not a recognized agent, left out of the name)')
    editors=values('item_editor_designer_names_1')
    editor=compact(editors[0]) if len(editors)==1 and ',' not in editors[0] else ''
    parts=[serial,found.group(1).lower(),title,parent,funnel,swimlane,iteration,*core,fmt,
           compact(asset),'Own'+owner]
    if ai:parts.append(ai)
    parts.append('Edt'+(editor or 'TBD'))
    parts.extend(tag_tokens(values('item_tags_labels_1')))
    name='_'.join(parts)
    note=('Final Name has TBD for: '+', '.join(missing)+'. Owner: please fill in these fields, then move '
          'this task back to Review - Editing to refresh the Final Name.') if missing else ''
    return {'name':name,'missing':missing,'note':note,'post_update':bool(missing) and name!=old_name}


def naming_columns(cfg):
    validate(cfg)
    editor = {'personsAndTeams': ([{'id':int(cfg['editor_id']),'kind':'person'}] if cfg.get('editor_id') else [])}
    return {EDITOR_COLUMN:editor,ITERATION_COLUMN:{'labels':[cfg['iteration_type']]},
            FORMAT_COLUMN:{'labels':[cfg['format']]},
            'text_mkrxd768':cfg['parent_serial']}

def is_iteration(cfg):
    return bool(cfg.get('parent_serial')) and cfg.get('parent_serial') != 'Pnone'

def prepare(cfg, monday=None):
    """Validate before any creation; resuming reads the real saved output version."""
    validate(cfg)
    if monday is not None:
        schema=monday('query { boards(ids:[9298353728]) { columns { id title type settings_str } } }')['data']['boards'][0]['columns']
        validate_schema(schema,cfg)
    if cfg.get('item_id'):
        if monday is None:raise ValueError('Resume needs authenticated Final Name readback')
        result=monday('query ($ids:[ID!]) { items(ids:$ids) { column_values(ids:["long_text_mkrxjtnx","multiple_person_mkrwpfa6"]) { id text value } } }',{'ids':[str(cfg['item_id'])]})
        rows={row['id']:row for row in result['data']['items'][0]['column_values']}
        cfg['existing_final_name']=rows[FINAL_NAME_COLUMN]['text']
        editor=rows.get(EDITOR_COLUMN,{})
        value=editor.get('value')
        if isinstance(value,str):value=json.loads(value)
        people=(value or {}).get('personsAndTeams',[])
        if len(people)>1:raise ValueError('Naming requires exactly one editor or blank')
        cfg['editor_name']=str(editor.get('text') or '').strip()
        cfg['editor_id']=people[0]['id'] if people else None
        match=re.match(r'(CO[0-9]+)_',str(cfg['existing_final_name']))
        if not match:raise ValueError('Existing Final Name is missing its output serial/version')
        version(match.group(1),cfg)
    return naming_columns(cfg)

def verify_rows(rows,cfg,serial=None):
    for column,expected in ((ITERATION_COLUMN,cfg['iteration_type']),
                            (FORMAT_COLUMN,cfg['format']),
                            ('text_mkrxd768',cfg['parent_serial']),
                            ('color_mm3y9jqt',FUNNEL_LABELS[cfg['creative_funnel'].upper()]),
                            ('color_mkrxsgqr',cfg['swimlane']),('color_mkrxa713','Video')):
        if str(rows.get(column,{}).get('text') or '').strip()!=expected:
            raise RuntimeError('Final naming readback mismatch: '+column)
    # AI Agent: an unversioned agent ('Cole') also matches its versioned label ('Cole 2.1');
    # the opener checks the exact active version label separately.
    agent=str(cfg.get('_ai_agent_name') or cfg.get('ai_agent') or '').strip()
    live_agent=str(rows.get('color_mm4h23be',{}).get('text') or '').strip()
    if live_agent!=agent:
        want=AGENT_LABEL_RE.fullmatch(agent); got=AGENT_LABEL_RE.fullmatch(live_agent)
        if not (want and got and want.group(1)==got.group(1) and want.group(2) is None):
            raise RuntimeError('Final naming readback mismatch: color_mm4h23be')
    owner=rows.get(OWNER_COLUMN,{}).get('value')
    if isinstance(owner,str):owner=json.loads(owner)
    if not isinstance(owner,dict) or owner.get('personsAndTeams') != [{'id':int(cfg['owner_id']),'kind':'person'}]:
        raise RuntimeError('final Monday Owner verification failed')
    editor=rows.get(EDITOR_COLUMN,{})
    if str(editor.get('text') or '').strip()!=str(cfg.get('editor_name') or ''):
        raise RuntimeError('Final naming Editor readback mismatch')
    editor_value=editor.get('value')
    if isinstance(editor_value,str):editor_value=json.loads(editor_value)
    expected_editor=([{'id':int(cfg['editor_id']),'kind':'person'}] if cfg.get('editor_id') else [])
    if (editor_value or {}).get('personsAndTeams',[])!=expected_editor:
        raise RuntimeError('Final naming Editor ID readback mismatch')
    expected_tags=tag_tokens(cfg.get('tags'))
    if expected_tags or TAGS_COLUMN in rows:
        tag_row=rows.get(TAGS_COLUMN,{})
        tag_value=tag_row.get('value')
        if isinstance(tag_value,str) and tag_value:tag_value=json.loads(tag_value)
        live_ids=sorted(int(i) for i in ((tag_value or {}).get('tag_ids') or []))
        want_ids=sorted(int(i) for i in (cfg.get('_tag_ids') or []))
        if expected_tags and want_ids and live_ids!=want_ids:
            raise RuntimeError('final Monday Tags verification failed')
        if tag_tokens(str(tag_row.get('text') or ''))!=expected_tags:
            raise RuntimeError('final Monday Tags verification failed')
    if serial is None:serial=cfg.get('_expected_serial')
    if serial is None:
        text=str(rows.get(FINAL_NAME_COLUMN,{}).get('text') or '')
        match=re.match(r'(CO[0-9]+)_',text)
        if not match:raise RuntimeError('Missing Final Name readback')
        serial=match.group(1)
    if rows.get(FINAL_NAME_COLUMN,{}).get('text')!=build(serial,cfg):
        raise RuntimeError('Final Name readback mismatch')
    return rows

READBACK_IDS = [ITERATION_COLUMN,FORMAT_COLUMN,FINAL_NAME_COLUMN,OWNER_COLUMN,EDITOR_COLUMN,
                'text_mkrxd768','color_mm3y9jqt','color_mkrxsgqr','color_mkrxa713',
                'color_mm4h23be',TAGS_COLUMN]
# Core label columns are deliberately NOT in READBACK_IDS / verify_rows: the labeler fills them later.


def validate_schema(schema,cfg):
    """Read-only live binding gate; never create a naming label implicitly."""
    by_id={c['id']:c for c in schema}
    selected={ITERATION_COLUMN:cfg['iteration_type'],FORMAT_COLUMN:cfg['format'],
              'color_mm3y9jqt':FUNNEL_LABELS[cfg['creative_funnel'].upper()],
              'color_mkrxsgqr':cfg['swimlane'],'color_mkrxa713':'Video'}
    agent=str(cfg.get('_ai_agent_name') or cfg.get('ai_agent') or '')
    if agent:selected['color_mm4h23be']=agent
    for cid,label in selected.items():
        column=by_id.get(cid)
        if not column:raise ValueError('Missing live naming column: '+cid)
        settings=json.loads(column['settings_str'])
        labels=settings.get('labels',{})
        pairs=labels.items() if isinstance(labels,dict) else [(x['id'],x['name']) for x in labels]
        deactivated={str(x) for x in settings.get('deactivated_labels',[])}
        matches=[i for i,name in pairs if name==label and str(i) not in deactivated]
        if len(matches)!=1:raise ValueError('Missing/ambiguous/inactive live naming label: '+cid+' '+label)
    for cid,typ in ((OWNER_COLUMN,'people'),(EDITOR_COLUMN,'people'),(FINAL_NAME_COLUMN,'long_text'),('text_mkrxd768','text')):
        if by_id.get(cid,{}).get('type')!=typ:raise ValueError('Missing/wrong live naming column: '+cid)
