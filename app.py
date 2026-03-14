import streamlit as st
import random
import math
import plotly.graph_objects as go
from collections import defaultdict

# ─────────────────────────────────────────────────────────────
# DATA: US regions / states / cities with approximate lat/lon
# ─────────────────────────────────────────────────────────────

US_HIERARCHY = {
    "Northwest": {
        "Washington": {"Seattle": (47.6, -122.3), "Spokane": (47.6, -117.4), "Tacoma": (47.2, -122.4)},
        "Oregon": {"Portland": (45.5, -122.7), "Eugene": (44.0, -123.1), "Salem": (44.9, -123.0)},
        "Idaho": {"Boise": (43.6, -116.2), "Idaho Falls": (43.5, -112.0)},
    },
    "Southwest": {
        "California": {"Los Angeles": (34.0, -118.2), "San Francisco": (37.8, -122.4), "San Diego": (32.7, -117.2), "Sacramento": (38.6, -121.5)},
        "Arizona": {"Phoenix": (33.4, -112.1), "Tucson": (32.2, -110.9), "Flagstaff": (35.2, -111.6)},
        "Nevada": {"Las Vegas": (36.2, -115.1), "Reno": (39.5, -119.8)},
        "New Mexico": {"Albuquerque": (35.1, -106.6), "Santa Fe": (35.7, -105.9)},
    },
    "Midwest": {
        "Illinois": {"Chicago": (41.9, -87.6), "Springfield": (39.8, -89.6), "Peoria": (40.7, -89.6)},
        "Ohio": {"Columbus": (39.9, -82.9), "Cleveland": (41.5, -81.7), "Cincinnati": (39.1, -84.5)},
        "Michigan": {"Detroit": (42.3, -83.0), "Grand Rapids": (42.9, -85.7), "Lansing": (42.7, -84.6)},
        "Minnesota": {"Minneapolis": (44.9, -93.3), "Saint Paul": (44.9, -93.1), "Duluth": (46.8, -92.1)},
        "Wisconsin": {"Milwaukee": (43.0, -87.9), "Madison": (43.1, -89.4)},
    },
    "South": {
        "Texas": {"Houston": (29.8, -95.4), "Dallas": (32.8, -96.8), "Austin": (30.3, -97.7), "San Antonio": (29.4, -98.5)},
        "Florida": {"Miami": (25.8, -80.2), "Orlando": (28.5, -81.4), "Tampa": (28.0, -82.5), "Jacksonville": (30.3, -81.7)},
        "Georgia": {"Atlanta": (33.7, -84.4), "Savannah": (32.1, -81.1), "Augusta": (33.5, -82.0)},
        "North Carolina": {"Charlotte": (35.2, -80.8), "Raleigh": (35.8, -78.6)},
        "Tennessee": {"Nashville": (36.2, -86.8), "Memphis": (35.1, -90.0), "Knoxville": (35.9, -83.9)},
    },
    "Northeast": {
        "New York": {"New York City": (40.7, -74.0), "Buffalo": (42.9, -78.9), "Albany": (42.7, -73.8), "Rochester": (43.2, -77.6)},
        "Massachusetts": {"Boston": (42.4, -71.1), "Worcester": (42.3, -71.8), "Springfield MA": (42.1, -72.6)},
        "Pennsylvania": {"Philadelphia": (39.9, -75.2), "Pittsburgh": (40.4, -80.0), "Harrisburg": (40.3, -76.9)},
        "New Jersey": {"Newark": (40.7, -74.2), "Trenton": (40.2, -74.7)},
        "Connecticut": {"Hartford": (41.8, -72.7), "New Haven": (41.3, -72.9)},
    },
}


# ─────────────────────────────────────────────────────────────
# TREE NODE CLASS
# ─────────────────────────────────────────────────────────────

class TreeNode:
    def __init__(self, name, level, parent=None, lat=None, lon=None):
        self.name = name
        self.level = level
        self.parent = parent
        self.children = []
        self.lat = lat
        self.lon = lon
        self.registered_users = []
        self.forwarding_pointers = {}
        self.replicated_locations = {}

    def path_to_root(self):
        path = []
        node = self
        while node:
            path.append(node)
            node = node.parent
        return path

    def __repr__(self):
        return f"TreeNode({self.name}, L{self.level})"


# ─────────────────────────────────────────────────────────────
# BUILD TREE
# ─────────────────────────────────────────────────────────────

def build_tree(max_depth=3, max_branch=None):
    root = TreeNode("US_HLR", level=0, lat=39.8, lon=-98.6)
    all_nodes = {"US_HLR": root}
    leaves = []

    regions = list(US_HIERARCHY.keys())
    if max_branch:
        regions = regions[:max_branch]

    for region_name in regions:
        region_node = TreeNode(region_name, level=1, parent=root)
        root.children.append(region_node)
        all_nodes[region_name] = region_node

        if max_depth < 2:
            leaves.append(region_node)
            continue

        states = list(US_HIERARCHY[region_name].keys())
        if max_branch:
            states = states[:max_branch]

        for state_name in states:
            state_node = TreeNode(state_name, level=2, parent=region_node)
            region_node.children.append(state_node)
            all_nodes[state_name] = state_node

            if max_depth < 3:
                leaves.append(state_node)
                continue

            cities = list(US_HIERARCHY[region_name][state_name].keys())
            if max_branch:
                cities = cities[:max_branch]

            for city_name in cities:
                lat, lon = US_HIERARCHY[region_name][state_name][city_name]
                city_node = TreeNode(city_name, level=3, parent=state_node, lat=lat, lon=lon)
                state_node.children.append(city_node)
                all_nodes[city_name] = city_node
                leaves.append(city_node)

    _assign_coords(root)
    return root, all_nodes, leaves


def _assign_coords(node):
    if node.lat is not None and node.lon is not None:
        return node.lat, node.lon
    if not node.children:
        return None, None
    lats, lons = [], []
    for c in node.children:
        la, lo = _assign_coords(c)
        if la is not None:
            lats.append(la)
            lons.append(lo)
    if lats:
        node.lat = sum(lats) / len(lats)
        node.lon = sum(lons) / len(lons)
    return node.lat, node.lon


# ─────────────────────────────────────────────────────────────
# USER CLASS
# ─────────────────────────────────────────────────────────────

class User:
    def __init__(self, uid, home_leaf):
        self.uid = uid
        self.home_leaf = home_leaf
        self.current_leaf = home_leaf
        self.calls_made = 0
        self.calls_received = 0
        self.moves = 0

    @property
    def cmr(self):
        total_calls = self.calls_made + self.calls_received
        if self.moves == 0:
            return float('inf') if total_calls > 0 else 0
        return total_calls / self.moves


# ─────────────────────────────────────────────────────────────
# FIND LCA
# ─────────────────────────────────────────────────────────────

def find_lca(node_a, node_b):
    path_a = node_a.path_to_root()
    path_b_set = {n.name for n in node_b.path_to_root()}
    for n in path_a:
        if n.name in path_b_set:
            return n
    return None


# ─────────────────────────────────────────────────────────────
# ROUTING METHODS
# ─────────────────────────────────────────────────────────────

def route_call_via_root(caller_leaf, callee_leaf, root, all_nodes):
    path_up = []
    n = caller_leaf
    while n:
        path_up.append(n)
        n = n.parent

    path_down_rev = []
    n = callee_leaf
    while n and n.name != root.name:
        path_down_rev.append(n)
        n = n.parent
    path_down = list(reversed(path_down_rev))

    full_path = path_up + path_down
    cost = len(full_path) - 1
    return full_path, cost, "Via Root (No Optimization)"


def route_call_lca(caller_leaf, callee_leaf, all_nodes):
    lca = find_lca(caller_leaf, callee_leaf)

    path_up = []
    n = caller_leaf
    while n and n.name != lca.name:
        path_up.append(n)
        n = n.parent
    path_up.append(lca)

    path_down = []
    n = callee_leaf
    while n and n.name != lca.name:
        path_down.append(n)
        n = n.parent
    path_down.reverse()

    full_path = path_up + path_down
    cost = len(full_path) - 1
    return full_path, cost, f"LCA ({lca.name})"


def route_call_with_forwarding(caller_leaf, callee_leaf, all_nodes, callee_uid, forwarding_level):
    path_up = []
    n = caller_leaf
    found_fwd = None

    while n:
        path_up.append(n)
        if callee_uid in n.forwarding_pointers:
            target_name = n.forwarding_pointers[callee_uid]
            if target_name in all_nodes:
                found_fwd = (n, all_nodes[target_name])
                break
        n = n.parent

    if found_fwd:
        fwd_node, target_node = found_fwd
        lca2 = find_lca(fwd_node, target_node)

        path_mid = []
        nn = fwd_node
        while nn and nn.name != lca2.name:
            nn = nn.parent
            if nn:
                path_mid.append(nn)

        path_down = []
        nn = target_node
        while nn and nn.name != lca2.name:
            path_down.append(nn)
            nn = nn.parent
        path_down.reverse()

        full_path = path_up + path_mid + path_down
        deduped = [full_path[0]]
        for p in full_path[1:]:
            if p.name != deduped[-1].name:
                deduped.append(p)
        cost = len(deduped) - 1
        return deduped, cost, f"Forwarding (at L{fwd_node.level}: {fwd_node.name})"

    return route_call_lca(caller_leaf, callee_leaf, all_nodes)


def route_call_with_replication(caller_leaf, callee_leaf, root, all_nodes, callee_uid):
    n = caller_leaf
    path_up = []

    while n:
        path_up.append(n)
        if callee_uid in n.replicated_locations:
            target_name = n.replicated_locations[callee_uid]
            if target_name in all_nodes:
                target_node = all_nodes[target_name]

                path_down_rev = []
                nn = target_node
                while nn and nn.name != n.name:
                    path_down_rev.append(nn)
                    nn = nn.parent
                path_down = list(reversed(path_down_rev))

                full_path = path_up + path_down
                deduped = [full_path[0]]
                for p in full_path[1:]:
                    if p.name != deduped[-1].name:
                        deduped.append(p)

                return deduped, len(deduped) - 1, f"Replication (at L{n.level}: {n.name})"
        n = n.parent

    return route_call_via_root(caller_leaf, callee_leaf, root, all_nodes)


# ─────────────────────────────────────────────────────────────
# FORWARDING POINTERS
# ─────────────────────────────────────────────────────────────

def set_forwarding_pointers(user, old_leaf, new_leaf, forwarding_level):
    n = old_leaf
    while n and n.level >= forwarding_level:
        n.forwarding_pointers[user.uid] = new_leaf.name
        n = n.parent


def clear_forwarding_pointers(user, all_nodes):
    for node in all_nodes.values():
        if user.uid in node.forwarding_pointers:
            del node.forwarding_pointers[user.uid]


# ─────────────────────────────────────────────────────────────
# REPLICATION
# ─────────────────────────────────────────────────────────────

def update_replication(user, all_nodes, cmr_threshold, replication_level):
    for node in all_nodes.values():
        if user.uid in node.replicated_locations:
            del node.replicated_locations[user.uid]

    if user.cmr >= cmr_threshold:
        n = user.current_leaf
        while n and n.level >= replication_level:
            n.replicated_locations[user.uid] = user.current_leaf.name
            n = n.parent


def compute_update_cost(user, all_nodes):
    count = 0
    for node in all_nodes.values():
        if user.uid in node.replicated_locations:
            count += 1
    return count


# ─────────────────────────────────────────────────────────────
# CALL COLORS
# ─────────────────────────────────────────────────────────────

CALL_COLORS = [
    'red', 'blue', 'green', 'purple', 'orange',
    'cyan', 'magenta', 'gold', 'lime', 'deeppink',
    'darkorange', 'dodgerblue', 'mediumseagreen', 'crimson', 'slateblue',
    'peru', 'teal', 'salmon', 'indigo', 'olive',
    'chocolate', 'darkviolet', 'tomato', 'steelblue', 'forestgreen',
    'hotpink', 'navy', 'sienna', 'springgreen', 'maroon',
    'turquoise', 'orangered', 'royalblue', 'darkgreen', 'coral',
    'mediumpurple', 'goldenrod', 'cadetblue', 'firebrick', 'darkturquoise',
    'yellowgreen', 'plum', 'seagreen', 'indianred', 'mediumvioletred',
    'limegreen', 'darkslateblue', 'lightcoral', 'darkcyan', 'khaki'
]


# ─────────────────────────────────────────────────────────────
# VISUALIZATION: US MAP
# ─────────────────────────────────────────────────────────────

def draw_us_map_tree(root, all_nodes, users, call_paths_to_show=None, forwarding_edges=None):
    fig = go.Figure()

    # Tree edges
    edge_lats, edge_lons = [], []
    for name, node in all_nodes.items():
        if node.parent and node.lat and node.lon and node.parent.lat and node.parent.lon:
            edge_lats += [node.parent.lat, node.lat, None]
            edge_lons += [node.parent.lon, node.lon, None]

    fig.add_trace(go.Scattergeo(
        lat=edge_lats, lon=edge_lons,
        mode='lines',
        line=dict(width=1, color='lightgray'),
        name='Tree Edges',
        hoverinfo='none'
    ))

    level_colors = {0: 'red', 1: 'blue', 2: 'green', 3: 'orange'}
    level_names = {0: 'L0: HLR (Root)', 1: 'L1: Region', 2: 'L2: State', 3: 'L3: City (VLR)'}

    for level in range(4):
        lats, lons, texts, sizes = [], [], [], []
        for name, node in all_nodes.items():
            if node.level == level and node.lat and node.lon:
                lats.append(node.lat)
                lons.append(node.lon)
                fwd_info = f" | Fwd: {list(node.forwarding_pointers.keys())}" if node.forwarding_pointers else ""
                repl_info = f" | Repl: {list(node.replicated_locations.keys())}" if node.replicated_locations else ""
                users_here = [u.uid for u in users.values() if u.current_leaf.name == name]
                user_info = f" | Users: {users_here}" if users_here else ""
                texts.append(f"{name} (L{level}){fwd_info}{repl_info}{user_info}")
                sizes.append(max(18 - level * 4, 6))

        if lats:
            fig.add_trace(go.Scattergeo(
                lat=lats, lon=lons,
                mode='markers+text',
                marker=dict(size=sizes, color=level_colors.get(level, 'black'),
                            line=dict(width=1, color='black')),
                text=[n.split(' (')[0] for n in texts],
                textposition='top center',
                textfont=dict(size=8),
                hovertext=texts,
                hoverinfo='text',
                name=level_names.get(level, f'L{level}')
            ))

    if call_paths_to_show:
        for i, call_info in enumerate(call_paths_to_show):
            path = call_info['path']
            call_num = call_info['call_num']
            caller = call_info['caller']
            callee = call_info['callee']
            method = call_info['method']
            cost = call_info['cost']
            event_num = call_info.get('event_num', call_num)
            color = CALL_COLORS[i % len(CALL_COLORS)]

            if path and len(path) > 1:
                path_lats = [n.lat for n in path if n.lat]
                path_lons = [n.lon for n in path if n.lon]
                hover_texts = [f"Event {event_num} Call #{call_num}: {n.name}" for n in path if n.lat]
                fig.add_trace(go.Scattergeo(
                    lat=path_lats, lon=path_lons,
                    mode='lines+markers',
                    line=dict(width=4, color=color),
                    marker=dict(size=10, color=color, symbol='diamond'),
                    name=f"E{event_num} #{call_num}: {caller}→{callee} (cost={cost})",
                    hovertext=hover_texts,
                    hoverinfo='text'
                ))

    if forwarding_edges:
        fwd_lats, fwd_lons = [], []
        for (n1, n2) in forwarding_edges:
            if n1.lat and n1.lon and n2.lat and n2.lon:
                fwd_lats += [n1.lat, n2.lat, None]
                fwd_lons += [n1.lon, n2.lon, None]
        if fwd_lats:
            fig.add_trace(go.Scattergeo(
                lat=fwd_lats, lon=fwd_lons,
                mode='lines',
                line=dict(width=2, color='purple', dash='dash'),
                name='Forwarding Pointers'
            ))

    fig.update_geos(
        scope='usa',
        showland=True, landcolor='lightyellow',
        showlakes=True, lakecolor='lightblue',
        showcountries=True
    )
    fig.update_layout(
        height=520, margin=dict(l=0, r=0, t=30, b=0),
        title="📍 Hierarchical Location Network on US Map",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, font=dict(size=10))
    )
    return fig


# ─────────────────────────────────────────────────────────────
# DRAW LOGICAL TREE
# ─────────────────────────────────────────────────────────────

def draw_logical_tree(root, all_nodes, users, call_paths_to_show=None):
    positions = {}
    _layout_tree(root, positions, x=0, y=0, x_span=100)

    fig = go.Figure()

    highlighted_edges = {}
    if call_paths_to_show:
        for i, call_info in enumerate(call_paths_to_show):
            path = call_info['path']
            color = CALL_COLORS[i % len(CALL_COLORS)]
            if path:
                path_names = [n.name for n in path]
                for j in range(len(path_names) - 1):
                    a, b = path_names[j], path_names[j + 1]
                    highlighted_edges[(a, b)] = color
                    highlighted_edges[(b, a)] = color

    for name, node in all_nodes.items():
        if node.parent and name in positions and node.parent.name in positions:
            x0, y0 = positions[node.parent.name]
            x1, y1 = positions[name]
            edge_key1 = (node.parent.name, name)
            edge_key2 = (name, node.parent.name)

            if edge_key1 in highlighted_edges:
                color = highlighted_edges[edge_key1]
                width = 4
            elif edge_key2 in highlighted_edges:
                color = highlighted_edges[edge_key2]
                width = 4
            else:
                color = 'lightgray'
                width = 1

            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0, y1], mode='lines',
                line=dict(color=color, width=width),
                showlegend=False, hoverinfo='none'
            ))

    highlighted_nodes = {}
    if call_paths_to_show:
        for i, call_info in enumerate(call_paths_to_show):
            path = call_info['path']
            color = CALL_COLORS[i % len(CALL_COLORS)]
            if path:
                for n in path:
                    highlighted_nodes[n.name] = color

    level_colors_tree = {0: 'red', 1: 'royalblue', 2: 'green', 3: 'orange'}
    for name, (x, y) in positions.items():
        node = all_nodes[name]
        is_highlighted = name in highlighted_nodes
        users_here = [u.uid for u in users.values() if u.current_leaf.name == name]
        fwd_count = len(node.forwarding_pointers)
        repl_count = len(node.replicated_locations)
        hover = (f"{name}<br>Level: {node.level}<br>"
                 f"Users: {users_here}<br>"
                 f"Fwd ptrs: {fwd_count}<br>"
                 f"Replicated: {repl_count}")

        border_color = highlighted_nodes.get(name, 'black')
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode='markers+text',
            marker=dict(
                size=24 if is_highlighted else 16,
                color=level_colors_tree.get(node.level, 'black'),
                line=dict(width=4 if is_highlighted else 1, color=border_color)
            ),
            text=name if node.level <= 2 else name[:8],
            textposition='top center',
            textfont=dict(size=8 if node.level == 3 else 10),
            hovertext=hover,
            hoverinfo='text',
            showlegend=False
        ))

    fig.update_layout(
        height=380, margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, autorange='reversed'),
        title="🌲 Logical Tree Structure (Hierarchical Database)"
    )
    return fig


def _layout_tree(node, positions, x, y, x_span):
    positions[node.name] = (x, y)
    if not node.children:
        return
    n = len(node.children)
    child_span = x_span / max(n, 1)
    start_x = x - x_span / 2 + child_span / 2
    for i, child in enumerate(node.children):
        cx = start_x + i * child_span
        _layout_tree(child, positions, cx, y + 1, child_span * 0.9)


# ─────────────────────────────────────────────────────────────
# SIMULATION — INTERLEAVED moves and calls
# ─────────────────────────────────────────────────────────────

def run_simulation(users, all_nodes, leaves, root, num_calls, num_moves,
                   forwarding_enabled, forwarding_level,
                   replication_enabled, cmr_threshold, replication_level,
                   rng_seed):
    rng = random.Random(rng_seed)

    log = []
    costs_baseline = []
    costs_optimized = []
    update_costs = []
    all_call_paths = []
    all_events = []  # unified timeline of moves and calls
    user_list = list(users.values())

    # Reset
    for u in user_list:
        u.calls_made = 0
        u.calls_received = 0
        u.moves = 0
    for node in all_nodes.values():
        node.forwarding_pointers = {}
        node.replicated_locations = {}

    # ── Build interleaved event schedule ──
    # Distribute moves evenly among calls
    # e.g. 12 calls + 4 moves = 16 events, moves at positions [3, 7, 11, 15]
    total_events = num_calls + num_moves
    events = []

    if total_events > 0:
        # Place moves evenly
        move_positions = set()
        if num_moves > 0:
            spacing = total_events / num_moves
            for i in range(num_moves):
                pos = int((i + 1) * spacing) - 1
                pos = min(pos, total_events - 1)
                while pos in move_positions:
                    pos += 1
                if pos < total_events:
                    move_positions.add(pos)

        for i in range(total_events):
            if i in move_positions:
                events.append('move')
            else:
                events.append('call')

    # ── Execute events in order ──
    call_count = 0
    move_count = 0
    event_num = 0

    for event_type in events:
        event_num += 1

        if event_type == 'move':
            u = rng.choice(user_list)
            old_leaf = u.current_leaf
            new_leaf = rng.choice(leaves)

            # Ensure actual movement
            attempts = 0
            while new_leaf.name == old_leaf.name and attempts < 10:
                new_leaf = rng.choice(leaves)
                attempts += 1
            if new_leaf.name == old_leaf.name:
                continue

            u.moves += 1
            move_count += 1

            # Set forwarding pointers BEFORE moving
            if forwarding_enabled:
                set_forwarding_pointers(u, old_leaf, new_leaf, forwarding_level)

            # Unregister / register
            if u.uid in old_leaf.registered_users:
                old_leaf.registered_users = [x for x in old_leaf.registered_users if x != u.uid]
            new_leaf.registered_users.append(u.uid)
            u.current_leaf = new_leaf

            uc = 0
            if replication_enabled:
                update_replication(u, all_nodes, cmr_threshold, replication_level)
                uc = compute_update_cost(u, all_nodes)
                update_costs.append(uc)

            move_record = {
                'event_num': event_num,
                'type': 'move',
                'user': u.uid,
                'from': old_leaf.name,
                'to': new_leaf.name,
                'update_cost': uc
            }
            all_events.append(move_record)

            log.append(
                f"📱 Event {event_num} | MOVE #{move_count}: {u.uid} "
                f"{old_leaf.name} → {new_leaf.name}"
                f"{f' (update cost: {uc})' if replication_enabled else ''}"
            )

        elif event_type == 'call':
            caller = rng.choice(user_list)
            possible_callees = [u for u in user_list if u.uid != caller.uid]
            if not possible_callees:
                continue
            callee = rng.choice(possible_callees)

            caller.calls_made += 1
            callee.calls_received += 1
            call_count += 1

            # Baseline (via root)
            path_base, cost_base, method_base = route_call_via_root(
                caller.current_leaf, callee.current_leaf, root, all_nodes)
            costs_baseline.append(cost_base)

            # Optimized
            if forwarding_enabled:
                path_opt, cost_opt, method_opt = route_call_with_forwarding(
                    caller.current_leaf, callee.current_leaf, all_nodes,
                    callee.uid, forwarding_level)
            elif replication_enabled:
                path_opt, cost_opt, method_opt = route_call_with_replication(
                    caller.current_leaf, callee.current_leaf, root,
                    all_nodes, callee.uid)
            else:
                path_opt, cost_opt, method_opt = route_call_lca(
                    caller.current_leaf, callee.current_leaf, all_nodes)

            costs_optimized.append(cost_opt)

            saving = cost_base - cost_opt
            saving_pct = (saving / cost_base * 100) if cost_base > 0 else 0

            call_record = {
                'event_num': event_num,
                'call_num': call_count,
                'caller': caller.uid,
                'callee': callee.uid,
                'caller_loc': caller.current_leaf.name,
                'callee_loc': callee.current_leaf.name,
                'path': path_opt,
                'path_baseline': path_base,
                'cost': cost_opt,
                'cost_baseline': cost_base,
                'method': method_opt,
                'saving': saving
            }
            all_call_paths.append(call_record)
            all_events.append({
                'event_num': event_num,
                'type': 'call',
                **call_record
            })

            log.append(
                f"📞 Event {event_num} | CALL #{call_count}: "
                f"{caller.uid}@{caller.current_leaf.name} → "
                f"{callee.uid}@{callee.current_leaf.name} | "
                f"Baseline: {cost_base} | Optimized: {cost_opt} ({method_opt}) | "
                f"Saved: {saving} ({saving_pct:.0f}%)"
            )

            # Update replication after call
            if replication_enabled:
                update_replication(caller, all_nodes, cmr_threshold, replication_level)
                update_replication(callee, all_nodes, cmr_threshold, replication_level)

    return {
        'log': log,
        'costs_baseline': costs_baseline,
        'costs_optimized': costs_optimized,
        'update_costs': update_costs,
        'all_call_paths': all_call_paths,
        'all_events': all_events,
        'move_count': move_count,
        'call_count': call_count
    }


# ─────────────────────────────────────────────────────────────
# STREAMLIT APP
# ─────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="Hierarchical Location Scheme", layout="wide")
    st.title("📡 Hierarchical Location Scheme Simulator")
    st.markdown("""
    Simulates **interleaved** user movements and call routing in a hierarchical
    mobile location management scheme with **forwarding pointers** and **replication**.
    """)

    # ── Sidebar ──
    st.sidebar.header("🌲 Tree Configuration")
    tree_depth = st.sidebar.slider("Tree Depth", 1, 3, 3,
                                    help="1=Regions, 2=+States, 3=+Cities")
    max_branch = st.sidebar.slider("Max children per node", 2, 6, 4)

    st.sidebar.header("👤 Users")
    num_users = st.sidebar.slider("Number of Users", 2, 20, 6)

    st.sidebar.header("📞 Simulation")
    num_calls = st.sidebar.slider("Number of Calls", 1, 50, 12)
    num_moves = st.sidebar.slider("Number of User Moves", 0, 30, 4)

    st.sidebar.header("🎲 Randomness")
    if 'sim_seed' not in st.session_state:
        st.session_state.sim_seed = 42
    sim_seed = st.sidebar.number_input("Seed", min_value=1, max_value=9999,
                                        value=st.session_state.sim_seed)
    st.session_state.sim_seed = sim_seed
    if st.sidebar.button("🔄 Randomize Seed"):
        st.session_state.sim_seed = random.randint(1, 9999)
        st.rerun()

    st.sidebar.header("➡️ Forwarding Pointers")
    forwarding_enabled = st.sidebar.checkbox("Enable Forwarding Pointers", value=True)
    forwarding_level = st.sidebar.slider(
        "Forwarding Level", 0, tree_depth, 1,
        help="0=Root (broadest). Pointers set at this level and below.",
        disabled=not forwarding_enabled)

    st.sidebar.header("📋 Replication")
    replication_enabled = st.sidebar.checkbox("Enable Replication", value=False)
    if replication_enabled and forwarding_enabled:
        st.sidebar.warning("⚠️ Forwarding disabled to isolate replication effect")
        forwarding_enabled = False
    cmr_threshold = st.sidebar.slider("CMR Threshold", 0.5, 10.0, 1.0, 0.5,
                                       disabled=not replication_enabled)
    replication_level = st.sidebar.slider("Replication Level", 0, tree_depth, 0,
                                           disabled=not replication_enabled)

    # ── Build ──
    tree_rng = random.Random(st.session_state.sim_seed)
    root, all_nodes, leaves = build_tree(max_depth=tree_depth, max_branch=max_branch)

    users = {}
    for i in range(num_users):
        uid = f"U{i+1}"
        home = tree_rng.choice(leaves)
        u = User(uid, home)
        u.current_leaf = home
        home.registered_users.append(uid)
        users[uid] = u

    # ── Run Simulation ──
    results = run_simulation(
        users, all_nodes, leaves, root,
        num_calls=num_calls, num_moves=num_moves,
        forwarding_enabled=forwarding_enabled, forwarding_level=forwarding_level,
        replication_enabled=replication_enabled, cmr_threshold=cmr_threshold,
        replication_level=replication_level,
        rng_seed=st.session_state.sim_seed + 1000
    )

    all_call_paths = results['all_call_paths']
    all_events = results['all_events']
    costs_b = results['costs_baseline']
    costs_o = results['costs_optimized']
    update_costs = results['update_costs']

    # ── Event Timeline ──
    st.subheader("⏱️ Event Timeline (Interleaved Moves & Calls)")

    if all_events:
        timeline_parts = []
        for ev in all_events:
            if ev['type'] == 'move':
                timeline_parts.append(
                    f"<span style='background:#ffe0b2;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;'>"
                    f"E{ev['event_num']} 📱 {ev['user']} moves {ev['from']}→{ev['to']}</span>"
                )
            else:
                timeline_parts.append(
                    f"<span style='background:#c8e6c9;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;'>"
                    f"E{ev['event_num']} 📞 #{ev['call_num']} {ev['caller']}→{ev['callee']} "
                    f"(cost {ev['cost']})</span>"
                )
        st.markdown(" ".join(timeline_parts), unsafe_allow_html=True)
        st.caption("🟧 = User Move | 🟩 = Call | Events are interleaved: users move BETWEEN calls")
    else:
        st.info("No events generated")

    # ── Call Viewer ──
    st.subheader("🎛️ Call Viewer")

    calls_to_show = []
    view_mode = "none"

    if not all_call_paths:
        st.warning("No calls completed. Try increasing users or calls.")
    else:
        max_idx = len(all_call_paths) - 1
        if 'selected_call_idx' not in st.session_state:
            st.session_state.selected_call_idx = 0
        if st.session_state.selected_call_idx > max_idx:
            st.session_state.selected_call_idx = max_idx
        if st.session_state.selected_call_idx < 0:
            st.session_state.selected_call_idx = 0

        viewer_col1, viewer_col2 = st.columns([1, 3])

        with viewer_col1:
            view_mode = st.radio(
                "View mode",
                ["Single call", "All calls", "Range of calls"],
                index=0
            )

        with viewer_col2:
            if view_mode == "Single call":
                call_options = [
                    f"Call #{c['call_num']} (Event {c['event_num']}): "
                    f"{c['caller']}@{c['caller_loc']} → "
                    f"{c['callee']}@{c['callee_loc']} "
                    f"(cost={c['cost']}, {c['method']})"
                    for c in all_call_paths
                ]

                def go_prev():
                    st.session_state.selected_call_idx = max(
                        0, st.session_state.selected_call_idx - 1)

                def go_next():
                    st.session_state.selected_call_idx = min(
                        len(all_call_paths) - 1,
                        st.session_state.selected_call_idx + 1)

                selected_idx = st.selectbox(
                    "Select call to view",
                    range(len(call_options)),
                    index=st.session_state.selected_call_idx,
                    format_func=lambda i: call_options[i],
                    key="call_selectbox"
                )
                st.session_state.selected_call_idx = selected_idx

                nav1, nav2, nav3 = st.columns([1, 1, 4])
                with nav1:
                    st.button("⬅️ Previous", on_click=go_prev,
                              disabled=(st.session_state.selected_call_idx == 0))
                with nav2:
                    st.button("Next ➡️", on_click=go_next,
                              disabled=(st.session_state.selected_call_idx >= max_idx))
                with nav3:
                    st.caption(
                        f"Viewing call {st.session_state.selected_call_idx + 1} "
                        f"of {len(all_call_paths)}"
                    )

                calls_to_show = [all_call_paths[st.session_state.selected_call_idx]]

            elif view_mode == "Range of calls":
                if len(all_call_paths) > 1:
                    range_vals = st.slider(
                        "Call range",
                        1, len(all_call_paths),
                        (1, min(5, len(all_call_paths)))
                    )
                    calls_to_show = all_call_paths[range_vals[0] - 1: range_vals[1]]
                else:
                    calls_to_show = all_call_paths

            else:
                calls_to_show = all_call_paths

        if len(calls_to_show) > 1:
            legend_parts = []
            for i, c in enumerate(calls_to_show):
                clr = CALL_COLORS[i % len(CALL_COLORS)]
                legend_parts.append(
                    f"<span style='color:{clr};font-weight:bold'>"
                    f"#{c['call_num']}: {c['caller']}→{c['callee']}</span>"
                )
            st.markdown("**Visible calls:** " + " | ".join(legend_parts),
                        unsafe_allow_html=True)

    # ── Forwarding edges ──
    fwd_edges = []
    for name, node in all_nodes.items():
        for uid, target_name in node.forwarding_pointers.items():
            if target_name in all_nodes:
                fwd_edges.append((node, all_nodes[target_name]))

    # ── Map ──
    fig_map = draw_us_map_tree(
        root, all_nodes, users,
        calls_to_show if calls_to_show else None,
        fwd_edges
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # ── Tree below map ──
    fig_tree = draw_logical_tree(
        root, all_nodes, users,
        calls_to_show if calls_to_show else None
    )
    st.plotly_chart(fig_tree, use_container_width=True)

    # ── Call detail card ──
    if calls_to_show and view_mode == "Single call":
        c = calls_to_show[0]
        st.markdown("---")
        dc1, dc2, dc3, dc4, dc5 = st.columns(5)
        dc1.metric("Caller", f"{c['caller']} @ {c['caller_loc']}")
        dc2.metric("Callee", f"{c['callee']} @ {c['callee_loc']}")
        dc3.metric("Baseline Cost", f"{c['cost_baseline']} hops")
        dc4.metric("Optimized Cost", f"{c['cost']} hops")
        dc5.metric("Saving", f"{c['saving']} hops",
                    delta=f"-{c['saving']}" if c['saving'] > 0 else "0")
        st.caption(
            f"**Event #{c['event_num']}** | **Method:** {c['method']}  \n"
            f"**Path:** {' → '.join(n.name for n in c['path'])}"
        )

    # ── Aggregate Metrics ──
    st.subheader("📊 Aggregate Performance Metrics")

    avg_baseline = sum(costs_b) / len(costs_b) if costs_b else 0
    avg_opt = sum(costs_o) / len(costs_o) if costs_o else 0
    avg_update = sum(update_costs) / len(update_costs) if update_costs else 0
    saving_pct = ((avg_baseline - avg_opt) / avg_baseline * 100) if avg_baseline > 0 else 0
    total_search = sum(costs_o)
    total_update = sum(update_costs)

    mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
    mc1.metric("Avg Baseline", f"{avg_baseline:.2f}")
    mc2.metric("Avg Optimized", f"{avg_opt:.2f}")
    mc3.metric("Saving %", f"{saving_pct:.1f}%",
               delta=f"-{avg_baseline - avg_opt:.1f} hops" if avg_baseline > avg_opt else None)
    mc4.metric("Total Search", f"{total_search}")
    mc5.metric("Total Update", f"{total_update}")
    mc6.metric("Tree Nodes", len(all_nodes))

    strategy = "No Optimization (LCA only)"
    if forwarding_enabled:
        strategy = f"Forwarding Pointers (level ≥ {forwarding_level})"
    elif replication_enabled:
        strategy = f"Replication (CMR ≥ {cmr_threshold})"
    st.info(
        f"**Active Strategy:** {strategy} | "
        f"**Calls:** {results['call_count']} | "
        f"**Moves:** {results['move_count']} | "
        f"**Total Events:** {len(all_events)} | "
        f"**Seed:** {st.session_state.sim_seed}"
    )

    # ── Per-call bar chart ──
    st.subheader("📈 Per-Call Cost: Baseline vs Optimized")
    if costs_b:
        fig_cost = go.Figure()
        call_labels = [f"#{c['call_num']}" for c in all_call_paths]
        fig_cost.add_trace(go.Bar(
            x=call_labels, y=costs_b,
            name='Baseline (via Root)', marker_color='lightcoral'))
        fig_cost.add_trace(go.Bar(
            x=call_labels, y=costs_o,
            name='Optimized', marker_color='lightgreen'))
        fig_cost.update_layout(
            barmode='group', xaxis_title='Call #',
            yaxis_title='Cost (hops)', height=300, margin=dict(t=30))
        st.plotly_chart(fig_cost, use_container_width=True)

    # ── Cumulative chart ──
    if len(costs_b) > 1:
        st.subheader("📉 Cumulative Cost Over Time")
        cum_b = [sum(costs_b[:i + 1]) for i in range(len(costs_b))]
        cum_o = [sum(costs_o[:i + 1]) for i in range(len(costs_o))]
        fig_cum = go.Figure()
        fig_cum.add_trace(go.Scatter(
            x=list(range(1, len(cum_b) + 1)), y=cum_b,
            mode='lines+markers', name='Cumulative Baseline', line=dict(color='coral')))
        fig_cum.add_trace(go.Scatter(
            x=list(range(1, len(cum_o) + 1)), y=cum_o,
            mode='lines+markers', name='Cumulative Optimized', line=dict(color='green')))
        if update_costs:
            cum_u = [sum(update_costs[:i + 1]) for i in range(len(update_costs))]
            fig_cum.add_trace(go.Scatter(
                x=list(range(1, len(cum_u) + 1)), y=cum_u,
                mode='lines+markers', name='Cumulative Updates', line=dict(color='orange')))
        fig_cum.update_layout(
            xaxis_title='Call #', yaxis_title='Cumulative Cost',
            height=300, margin=dict(t=30))
        st.plotly_chart(fig_cum, use_container_width=True)

    # ── Cost variation chart (shows costs are NOT all the same) ──
    if costs_o and len(set(costs_o)) > 1:
        st.subheader("🔀 Cost Variation Across Calls")
        unique_costs = sorted(set(costs_o))
        cost_counts = [costs_o.count(c) for c in unique_costs]
        fig_var = go.Figure()
        fig_var.add_trace(go.Bar(
            x=[str(c) for c in unique_costs], y=cost_counts,
            marker_color='steelblue'))
        fig_var.update_layout(
            xaxis_title='Cost (hops)', yaxis_title='Number of Calls',
            height=250, margin=dict(t=30), title="Distribution of Call Costs")
        st.plotly_chart(fig_var, use_container_width=True)

    # ── Replication Details ──
    if replication_enabled:
        st.subheader("📋 Replication & CMR Analysis")
        cr1, cr2 = st.columns(2)
        with cr1:
            cmr_data = []
            for u in users.values():
                tc = u.calls_made + u.calls_received
                cv = u.cmr
                cmr_data.append({
                    "User": u.uid,
                    "Calls": tc,
                    "Moves": u.moves,
                    "CMR": f"{cv:.2f}" if cv != float('inf') else "∞",
                    "Replicated": "✅" if cv >= cmr_threshold else "❌",
                    "Location": u.current_leaf.name
                })
            st.dataframe(cmr_data, use_container_width=True)
        with cr2:
            st.markdown(f"""
            **Trade-off Analysis:**
            - CMR Threshold: **{cmr_threshold}**
            - Total Search Cost: **{total_search}**
            - Total Update Cost: **{total_update}**
            - Net System Cost: **{total_search + total_update}**
            - High CMR → replication saves search cost
            - Low CMR → updates dominate
            """)

    # ── Forwarding Details ──
    if forwarding_enabled:
        st.subheader("🔗 Forwarding Pointers")
        fwd_table = []
        for name, node in all_nodes.items():
            for uid, target in node.forwarding_pointers.items():
                fwd_table.append({
                    "Node": name, "Level": node.level,
                    "User": uid, "Points To": target})
        if fwd_table:
            st.dataframe(fwd_table, use_container_width=True)
        else:
            st.info("No forwarding pointers active")

    # ── User Table ──
    st.subheader("👤 User Status")
    user_table = []
    for u in users.values():
        user_table.append({
            "ID": u.uid, "Home": u.home_leaf.name,
            "Current": u.current_leaf.name,
            "Sent": u.calls_made, "Received": u.calls_received,
            "Moves": u.moves,
            "CMR": f"{u.cmr:.2f}" if u.cmr != float('inf') else "∞"
        })
    st.dataframe(user_table, use_container_width=True)

    # ── Log ──
    with st.expander("📝 Full Event Log"):
        st.code("\n".join(results['log']) if results['log'] else "No events.",
                language="text")

    # ── Explanation ──
    with st.expander("📖 Technical Explanation"):
        st.markdown("""
### Hierarchical Location Scheme

| Level | Name | Role |
|-------|------|------|
| 0 | Root (HLR) | Global database |
| 1 | Region | Regional server |
| 2 | State | Area server |
| 3 | City (VLR) | Where users connect |

---

### Event Interleaving

Moves and calls are **interleaved** in time. This means:
- A user may move between calls
- Forwarding pointers set during a move can help subsequent calls
- Costs vary as users relocate during the simulation

Example timeline:
