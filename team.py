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
