def visible_sessions(states, limit=12):
    """Keep verified ancestors with priority sessions so their links remain visible."""
    nodes = {s['id']: s for s in states}
    selected = set()
    for state in states:
        family = set()
        current = state
        while current and current['id'] not in selected | family:
            family.add(current['id'])
            current = nodes.get(current.get('parent_id'))
        if len(selected | family) <= limit:
            selected.update(family)
    return [s for s in states if s['id'] in selected]


def selected_team(states, selected):
    """Follow only verified links among visible sessions; tolerate missing parents/cycles."""
    nodes={s['id']:s for s in states}
    if selected not in nodes:return None,set()
    root=selected;seen=set()
    while nodes[root].get('parent_id') in nodes and root not in seen:
        seen.add(root)
        parent=nodes[root]['parent_id']
        if parent in seen:break
        root=parent
    members={root}
    while True:
        children={key for key,node in nodes.items() if node.get('parent_id') in members}
        expanded=members|children
        if expanded==members:break
        members=expanded
    return root,members
