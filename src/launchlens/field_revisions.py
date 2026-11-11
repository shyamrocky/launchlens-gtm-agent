"""Bounded edits inside the existing revision/validation/review cycle."""
from launchlens.observability import step
from copy import deepcopy
import hashlib
from pathlib import Path
import re

from launchlens.content_review import check, model_brief
from launchlens.linkedin_drafting import digest
from launchlens.package_content import (package_value, text_fields, revision_phrase_targets,
    compare_revision_phrases, refinement_avoid_list, revision_flagged_locations)

PROTOCOL = 'targeted_fields_v1'
PROMPT_SHA = '27ca47f8e30677d9d1829155f15609f7b47f59b25e956b324facf039bb9c647e'


def prompt():
    raw = Path(__file__).with_name('prompts').joinpath('package_field_revision_v1.txt').read_bytes()
    check(hashlib.sha256(raw).hexdigest() == PROMPT_SHA, 'stale_binding')
    return raw.decode()


def set_text(package, name, path, text):
    target = package[name]['content']; parts = path.split('.')
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]
    target[int(parts[-1]) if isinstance(target, list) else parts[-1]] = text


def plan(state, permission):
    """Verify every selected span against the original field, never scope by notes."""
    from launchlens.review_decisions import grouped_findings, safe_hints
    source = deepcopy(state); source['revision_request'] = permission
    targets = revision_phrase_targets(source)
    feedback = permission['feedback']; groups = grouped_findings(state)
    if not targets and permission.get('origin') != 'agent' and not any(
            line.startswith(('Change ', 'Human prefers keeping ')) for line in feedback.splitlines()):
        # Older direct API callers supplied review guidance rather than a decision
        # book. Scope them to current flagged occurrences, never the whole package.
        targets = [dict(format=o['format'], content_field=o['content_field'], quote=o['quote'],
                        start=o['start'], end=o['end'])
                   for g in groups for o in g['occurrences']
                   if o['needs_attention'] and isinstance(o['start'], int)]
    check(bool(targets), 'permission_denied')
    replacements = []
    expression = r'Requested phrase replacement at (\w+)\.([\w.]+)\[(\d+):(\d+)\]: replace only “(.+)” with “(.+)”; preserve the rest of the sentence \(human preference; retain evidence and qualifications\)'
    for line in feedback.splitlines():
        if not line.startswith('Requested phrase replacement at '): continue
        match = re.fullmatch(expression, line); check(match is not None, 'permission_denied')
        name, path, start, end, quote, replacement = match.groups()
        target = next((t for t in targets if (t['format'], t['content_field'], t['start'], t['end'], t['quote']) ==
                       (name, path, int(start), int(end), quote)), None)
        check(target is not None and any(replacement in safe_hints(g) for g in groups
              if any((o['format'], o['content_field'], o['start'], o['end']) ==
                     (name, path, int(start), int(end)) for o in g['occurrences'])), 'permission_denied')
        replacements.append(dict(target, replacement=replacement))
    keeps = []
    for line in feedback.splitlines():
        match = re.fullmatch(r'Human prefers keeping “(.+)” at (.+)', line)
        if not match: continue
        quote, locations = match.groups()
        for location in locations.split(', '):
            match = re.fullmatch(r'(\w+)\.([\w.]+)\[(\d+):(\d+)\]', location)
            check(match is not None, 'permission_denied')
            name, path, start, end = match.groups()
            text = dict(text_fields(package_value(state)[name]['content'])).get(path, '')
            check(text[int(start):int(end)].casefold() == quote.casefold(), 'permission_denied')
            keeps.append(dict(format=name, content_field=path, start=int(start), end=int(end), quote=text[int(start):int(end)]))
    writer_targets = [t for t in targets if not any(t == {k:v for k,v in r.items() if k != 'replacement'} for r in replacements)]
    # Exact edits may shift later requests or already replace an overlapping
    # phrase. Writer coordinates must refer to the actual text it receives.
    temporary=deepcopy(state)
    temporary['revision_request']={'field_plan':{'replacements':replacements}}
    base=exact_package(temporary)
    writer_targets=[dict(format=t['format'],content_field=t['content_field'],quote=t['quote'],
        start=t['current_start'],end=t['current_end'])
        for t in compare_revision_phrases(package_value(state),base,writer_targets) if t['status']=='unresolved']
    notes = '\n'.join(line for line in feedback.splitlines() if not line.startswith(
        ('Change ', 'Human prefers keeping ', 'Requested phrase replacement at ', 'Human wording feedback only;')))
    return dict(protocol=PROTOCOL, prompt_sha256=PROMPT_SHA, targets=targets,
                replacements=replacements, keeps=keeps, writer_targets=writer_targets, notes=notes)


@step('exact-replacement apply', capture=())
def exact_package(state):
    value = package_value(state); selected = state['revision_request']['field_plan']['replacements']
    grouped = {}
    for row in selected: grouped.setdefault((row['format'], row['content_field']), []).append(row)
    for (name, path), rows in grouped.items():
        text = dict(text_fields(value[name]['content']))[path]; previous_start = len(text) + 1
        for row in sorted(rows, key=lambda r:r['start'], reverse=True):
            check(row['end'] <= previous_start and text[row['start']:row['end']] == row['quote'], 'permission_denied')
            text = text[:row['start']] + row['replacement'] + text[row['end']:]; previous_start = row['start']
        set_text(value, name, path, text)
    return value


def prepare(state, inputs, binding, projector):
    permission = state['revision_request']; selected = permission['field_plan']; base = exact_package(state)
    brief, manifest = model_brief(inputs, projector)
    # The original evidence, qualifiers and launch restrictions stay available;
    # remove duplicate whole-package schemas, templates and review transcripts.
    brief = {k:deepcopy(v) for k,v in brief.items() if k in (
        'validated_request','research_context','draft_constraints','voice_policy','tone_policy','package_contract')}
    fields = {}; properties = {}
    current_keeps=[dict(format=t['format'],content_field=t['content_field'],quote=t['quote'],start=t['current_start'],end=t['current_end']) for t in compare_revision_phrases(package_value(state),base,selected['keeps']) if t['status']=='unresolved']
    paths = sorted({(t['format'],t['content_field']) for t in selected['writer_targets']})
    for index, (name,path) in enumerate(paths):
        identity = 'field_' + str(index); text = dict(text_fields(base[name]['content']))[path]
        fields[identity] = dict(format=name, content_field=path, text=text, source_sha256=digest(text),
            requests=[t for t in selected['writer_targets'] if (t['format'],t['content_field']) == (name,path)],
            kept_occurrences=[t for t in current_keeps if (t['format'],t['content_field']) == (name,path)],
            approved_replacements=[t for t in selected['replacements'] if (t['format'],t['content_field']) == (name,path)])
        properties[identity] = {'type':'object','additionalProperties':False,
            'required':['source_sha256','text','claim_ids'], 'properties':{
                'source_sha256':{'type':'string','const':digest(text)},
                'text':{'type':'string','minLength':1,'maxLength':20000},
                'claim_ids':{'type':'array','uniqueItems':True,'items':{'type':'string','enum':inputs['draft_constraints']['allowed_claim_ids']}}}}
    formats = {name for name,_ in paths}
    if 'tone_policy' in brief:
        brief['tone_policy']['format_specs'] = {k:v for k,v in brief['tone_policy']['format_specs'].items() if k in formats}
    return dict(binding=binding, revision_protocol=PROTOCOL, revision_origin=permission.get('origin','human'), revision_command_id=permission['command_id'],
        writer_brief=brief, targeted_fields=fields, owner_notes_data_only=selected['notes'],
        full_avoid_list=refinement_avoid_list(inputs), current_flagged_locations=revision_flagged_locations(state),
        projection_manifest=manifest, output_schema={'type':'object','additionalProperties':False,
            'required':['source_package_sha256','edits'],'properties':{
                'source_package_sha256':{'type':'string','const':binding['draft_sha256']},
                'edits':{'type':'object','additionalProperties':False,'required':list(properties),'properties':properties}}})


def merge(state, model_input, response):
    fields = model_input['targeted_fields']; base = exact_package(state); value = deepcopy(base)
    check(type(response) is dict and set(response) == {'source_package_sha256','edits'} and
          response['source_package_sha256'] == model_input['binding']['draft_sha256'] and
          type(response['edits']) is dict and set(response['edits']) == set(fields), 'invalid_response')
    allowed = model_input['writer_brief']['draft_constraints']['allowed_claim_ids']
    for identity, field in fields.items():
        edit = response['edits'][identity]
        check(type(edit) is dict and set(edit) == {'source_sha256','text','claim_ids'} and
              edit['source_sha256'] == field['source_sha256'] and type(edit['text']) is str and
              0 < len(edit['text'].strip()) <= 20000 and type(edit['claim_ids']) is list and
              all(type(c) is str and c in allowed for c in edit['claim_ids']) and
              len(edit['claim_ids']) == len(set(edit['claim_ids'])), 'invalid_response')
        name,path = field['format'],field['content_field'];set_text(value,name,path,edit['text'])
        refs = [r for r in value[name]['claim_references'] if r['content_field'] != path]
        if edit['claim_ids']: refs.append({'content_field':path,'claim_ids':edit['claim_ids']})
        value[name]['claim_references'] = refs
    selected = state['revision_request']['field_plan']
    locked = selected['keeps']
    for row in compare_revision_phrases(package_value(state), value, locked):
        check(row['status'] == 'unresolved' and dict(text_fields(value[row['format']]['content']))[row['content_field']][row['current_start']:row['current_end']] == row['quote'], 'permission_denied')
    # Exact replacements must also survive a mixed field rewrite. Construct their
    # spans in the deterministic base, then use the same occurrence alignment.
    for replacement in selected['replacements']:
        name,path = replacement['format'],replacement['content_field']
        offset = replacement['start'] + sum(len(r['replacement'])-(r['end']-r['start']) for r in selected['replacements']
            if (r['format'],r['content_field']) == (name,path) and r['start'] < replacement['start'])
        target = dict(format=name,content_field=path,quote=replacement['replacement'],start=offset,end=offset+len(replacement['replacement']))
        row = compare_revision_phrases(base,value,[target])[0]
        check(row['status'] == 'unresolved' and dict(text_fields(value[name]['content']))[path][row['current_start']:row['current_end']] == replacement['replacement'], 'permission_denied')
    return value
