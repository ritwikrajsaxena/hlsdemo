import streamlit as st
import random
import math
import plotly.graph_objects as go
from collections import defaultdict
import json

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
        # forwarding_pointers: user_id -> target_node_name
        self.forwarding_pointers = {}
        # replicated_locations: user_id -> leaf_node_name
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
# BUILD TREE FROM US_HIERARCHY
# ─────────────────────────────────────────────────────────────

def build_tree(max_depth=3, max_branch=None):
    """
    Level 0: National Root (HLR)
    Level 1: Regions
    Level 2: States
    Level 3: Cities (leaves)
    max_depth: 1=regions only, 2=regions+states, 3=full
    max_branch: limit children per node (None=all)
    """
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

    # assign lat/lon to intermediate nodes as average of children
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
# ROUTE CALL: returns (path, cost, method_used)
# ─────────────────────────────────────────────────────────────

def route_call_basic(caller_leaf, callee_leaf, all_nodes):
    """Basic HLR lookup: go up to LCA, then down."""
    lca = find_lca(caller_leaf, callee_leaf)
    # path up from caller to LCA
    path_up = []
    n = caller_leaf
    while n and n.name != lca.name:
        path_up.append(n)
        n = n.parent
    path_up.append(lca)

    # path down from LCA to callee
    path_down = []
    n = callee_leaf
    while n and n.name != lca.name:
        path_down.append(n)
        n = n.parent
    path_down.reverse()

    full_path = path_up + path_down
    cost = len(full_path) - 1  # edges
    return full_path, cost, "Basic LCA"


def route_call_with_forwarding(caller_leaf, callee_leaf, all_nodes, callee_uid, forwarding_level):
    """
    Check forwarding pointers along the path up from caller.
    If a forwarding pointer for callee_uid is found at or below forwarding_level,
    follow it.
    """
    # walk up from caller looking for a forwarding pointer
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
        # now route from fwd_node down to target_node (the actual callee leaf may differ)
        # For simplicity, the forwarding pointer points to current leaf
        # path = path_up (to fwd_node) + path from fwd_node to target
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
        # deduplicate consecutive
        deduped = [full_path[0]]
        for p in full_path[1:]:
            if p.name != deduped[-1].name:
                deduped.append(p)
        cost = len(deduped) - 1
        return deduped, cost, f"Forwarding (found at L{fwd_node.level})"

    # fallback to basic
    return route_call_basic(caller_leaf, callee_leaf, all_nodes)


def route_call_with_replication(caller_leaf, callee_leaf, all_nodes, callee_uid):
    """
    Walk up from caller. If any node has replicated location for callee_uid,
    use that to short-circuit.
    """
    n = caller_leaf
    path_up = []
    while n:
        path_up.append(n)
        if callee_uid in n.replicated_locations:
            target_name = n.replicated_locations[callee_uid]
            if target_name in all_nodes:
                target_node = all_nodes[target_name]
                # go down to target
                path_down = []
                nn = target_node
                while nn and nn.name != n.name:
                    path_down.append(nn)
                    nn = nn.parent
                path_down.reverse()
                full_path = path_up + path_down
                deduped = [full_path[0]]
                for p in full_path[1:]:
                    if p.name != deduped[-1].name:
                        deduped.append(p)
                return deduped, len(deduped) - 1, f"Replication (found at L{n.level})"
        n = n.parent

    return route_call_basic(caller_leaf, callee_leaf, all_nodes)


# ─────────────────────────────────────────────────────────────
# SET FORWARDING POINTERS
# ─────────────────────────────────────────────────────────────

def set_forwarding_pointers(user, old_leaf, new_leaf, forwarding_level):
    """Set forwarding pointer at old_leaf and up to forwarding_level."""
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

def update_replication(user, all_nodes, cmr_threshold):
    """
    If user CMR >= threshold, replicate location info up the tree from current leaf.
    Otherwise, clear replication.
    """
    # clear old
    for node in all_nodes.values():
        if user.uid in node.replicated_locations:
            del node.replicated_locations[user.uid]

    if user.cmr >= cmr_threshold:
        n = user.current_leaf
        while n:
            n.replicated_locations[user.uid] = user.current_leaf.name
            n = n.parent


def compute_update_cost(user, all_nodes):
    """Cost to update location = number of nodes that have replicated info for this user."""
    count = 0
    for node in all_nodes.values():
        if user.uid in node.replicated_locations:
            count += 1
    return count


# ─────────────────────────────────────────────────────────────
# VISUALIZATION: US MAP WITH TREE
# ─────────────────────────────────────────────────────────────

def draw_us_map_tree(root, all_nodes, users, highlight_path=None, forwarding_edges=None):
    fig = go.Figure()

    # Draw edges of tree
    edge_lats = []
    edge_lons = []
    for name, node in all_nodes.items():
        if node.parent and node.lat and node.lon and node.parent.lat and node.parent.lon:
            edge_lats += [node.parent.lat, node.lat, None]
            edge_lons += [node.parent.lon, node.lon, None]

    fig.add_trace(go.Scattergeo(
        lat=edge_lats, lon=edge_lons,
        mode='lines',
        line=dict(width=1, color='gray'),
        name='Tree Edges',
        hoverinfo='none'
    ))

    # Color nodes by level
    level_colors = {0: 'red', 1: 'blue', 2: 'green', 3: 'orange'}
    level_names = {0: 'L0: HLR', 1: 'L1: Region', 2: 'L2: State', 3: 'L3: City'}

    for level in range(4):
        lats, lons, texts, sizes = [], [], [], []
        for name, node in all_nodes.items():
            if node.level == level and node.lat and node.lon:
                lats.append(node.lat)
                lons.append(node.lon)
                fwd_info = f" | Fwd ptrs: {list(node.forwarding_pointers.keys())}" if node.forwarding_pointers else ""
                repl_info = f" | Replicated: {list(node.replicated_locations.keys())}" if node.replicated_locations else ""
                users_here = [u.uid for u in users.values() if u.current_leaf.name == name]
                user_info = f" | Users: {users_here}" if users_here else ""
                texts.append(f"{name} (L{level}){fwd_info}{repl_info}{user_info}")
                sizes.append(max(18 - level * 4, 6))

        if lats:
            fig.add_trace(go.Scattergeo(
                lat=lats, lon=lons,
                mode='markers+text',
                marker=dict(size=sizes, color=level_colors.get(level, 'black'), line=dict(width=1, color='black')),
                text=[n.split(' (')[0] for n in texts],
                textposition='top center',
                textfont=dict(size=8),
                hovertext=texts,
                hoverinfo='text',
                name=level_names.get(level, f'L{level}')
            ))

    # Highlight call path
    if highlight_path and len(highlight_path) > 1:
        path_lats = [n.lat for n in highlight_path if n.lat]
        path_lons = [n.lon for n in highlight_path if n.lon]
        fig.add_trace(go.Scattergeo(
            lat=path_lats, lon=path_lons,
            mode='lines+markers',
            line=dict(width=4, color='red'),
            marker=dict(size=12, color='red', symbol='diamond'),
            name='Call Path',
            hovertext=[n.name for n in highlight_path],
            hoverinfo='text'
        ))

    # Forwarding pointer edges
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
        title="Hierarchical Location Scheme on US Map",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    return fig


# ─────────────────────────────────────────────────────────────
# DRAW LOGICAL TREE (Plotly Treemap or manual layout)
# ─────────────────────────────────────────────────────────────

def draw_logical_tree(root, all_nodes, users, highlight_path_names=None):
    """Draw tree as a top-down graph using plotly scatter."""
    positions = {}
    _layout_tree(root, positions, x=0, y=0, x_span=100)

    fig = go.Figure()

    # edges
    for name, node in all_nodes.items():
        if node.parent and name in positions and node.parent.name in positions:
            x0, y0 = positions[node.parent.name]
            x1, y1 = positions[name]
            color = 'red' if (highlight_path_names and node.parent.name in highlight_path_names and name in highlight_path_names) else 'lightgray'
            width = 3 if color == 'red' else 1
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0, y1], mode='lines',
                line=dict(color=color, width=width),
                showlegend=False, hoverinfo='none'
            ))

    # nodes
    level_colors_tree = {0: 'red', 1: 'royalblue', 2: 'green', 3: 'orange'}
    for name, (x, y) in positions.items():
        node = all_nodes[name]
        is_highlighted = highlight_path_names and name in highlight_path_names
        users_here = [u.uid for u in users.values() if u.current_leaf.name == name]
        fwd_count = len(node.forwarding_pointers)
        repl_count = len(node.replicated_locations)
        hover = f"{name}<br>Level: {node.level}<br>Users: {users_here}<br>Fwd ptrs: {fwd_count}<br>Replicated: {repl_count}"

        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode='markers+text',
            marker=dict(
                size=22 if is_highlighted else 16,
                color=level_colors_tree.get(node.level, 'black'),
                line=dict(width=3 if is_highlighted else 1, color='red' if is_highlighted else 'black')
            ),
            text=name if node.level <= 2 else name[:8],
            textposition='top center',
            textfont=dict(size=8 if node.level == 3 else 10),
            hovertext=hover,
            hoverinfo='text',
            showlegend=False
        ))

    fig.update_layout(
        height=400, margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, autorange='reversed'),
        title="Logical Tree Structure"
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
# SIMULATION
# ─────────────────────────────────────────────────────────────

def run_batch_simulation(users, all_nodes, leaves, num_calls, num_moves, forwarding_enabled, forwarding_level, replication_enabled, cmr_threshold):
    log = []
    search_costs_basic = []
    search_costs_optimized = []
    update_costs = []
    user_list = list(users.values())

    # Perform moves first
    for i in range(num_moves):
        u = random.choice(user_list)
        old_leaf = u.current_leaf
        new_leaf = random.choice(leaves)
        if new_leaf.name == old_leaf.name:
            continue
        u.moves += 1

        if forwarding_enabled:
            set_forwarding_pointers(u, old_leaf, new_leaf, forwarding_level)

        # unregister from old, register at new
        if u.uid in [x for x in old_leaf.registered_users]:
            old_leaf.registered_users = [x for x in old_leaf.registered_users if x != u.uid]
        new_leaf.registered_users.append(u.uid)
        u.current_leaf = new_leaf

        if replication_enabled:
            update_replication(u, all_nodes, cmr_threshold)
            uc = compute_update_cost(u, all_nodes)
            update_costs.append(uc)

        log.append(f"MOVE: {u.uid} moved from {old_leaf.name} → {new_leaf.name} (total moves: {u.moves})")

    # Perform calls
    last_path = None
    last_method = ""
    for i in range(num_calls):
        caller = random.choice(user_list)
        callee = random.choice(user_list)
        if caller.uid == callee.uid:
            continue

        caller.calls_made += 1
        callee.calls_received += 1

        # basic cost
        path_b, cost_b, _ = route_call_basic(caller.current_leaf, callee.current_leaf, all_nodes)
        search_costs_basic.append(cost_b)

        # optimized
        if forwarding_enabled:
            path_o, cost_o, method = route_call_with_forwarding(
                caller.current_leaf, callee.current_leaf, all_nodes, callee.uid, forwarding_level)
        elif replication_enabled:
            path_o, cost_o, method = route_call_with_replication(
                caller.current_leaf, callee.current_leaf, all_nodes, callee.uid)
        else:
            path_o, cost_o, method = path_b, cost_b, "Basic LCA"

        search_costs_optimized.append(cost_o)
        last_path = path_o
        last_method = method

        saving = cost_b - cost_o
        log.append(f"CALL #{i+1}: {caller.uid} → {callee.uid} | Basic cost: {cost_b} | Optimized cost: {cost_o} | Saving: {saving} | Method: {method}")

        # update replication after calls
        if replication_enabled:
            update_replication(caller, all_nodes, cmr_threshold)
            update_replication(callee, all_nodes, cmr_threshold)

    return log, search_costs_basic, search_costs_optimized, update_costs, last_path, last_method


# ─────────────────────────────────────────────────────────────
# STREAMLIT APP
# ─────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="Hierarchical Location Scheme", layout="wide")
    st.title("📡 Hierarchical Location Scheme Simulator")
    st.markdown("Simulates call routing, forwarding pointers, and replication in a hierarchical mobile location management scheme on a US map.")

    # ── Sidebar Controls ──
    st.sidebar.header("🌲 Tree Configuration")
    tree_depth = st.sidebar.slider("Tree Depth (max levels below root)", 1, 3, 3)
    max_branch = st.sidebar.slider("Max children per node (branching factor)", 2, 6, 5,
                                    help="Limits how many children each node can have")

    st.sidebar.header("👤 Users")
    num_users = st.sidebar.slider("Number of Users", 2, 20, 6)

    st.sidebar.header("📞 Simulation Parameters")
    num_calls = st.sidebar.slider("Number of Calls", 1, 50, 10)
    num_moves = st.sidebar.slider("Number of User Moves (Mobility)", 0, 30, 5)

    st.sidebar.header("➡️ Forwarding Pointers")
    forwarding_enabled = st.sidebar.checkbox("Enable Forwarding Pointers", value=True)
    forwarding_level = st.sidebar.slider("Forwarding Level (set pointers up to this level)", 0, tree_depth, max(0, tree_depth - 1),
                                          help="0 = root level (broadest), higher = more localized",
                                          disabled=not forwarding_enabled)

    st.sidebar.header("📋 Replication")
    replication_enabled = st.sidebar.checkbox("Enable Replication", value=False)
    cmr_threshold = st.sidebar.slider("CMR Threshold for Replication", 0.5, 10.0, 2.0, 0.5,
                                       help="Call-to-Mobility Ratio above which location is replicated up tree",
                                       disabled=not replication_enabled)

    st.sidebar.header("🎯 Manual Call")
    manual_mode = st.sidebar.checkbox("Manual Call Mode (pick caller/callee)")

    # ── Build Tree ──
    if 'seed' not in st.session_state:
        st.session_state.seed = 42

    if st.sidebar.button("🔄 Regenerate (new random seed)"):
        st.session_state.seed = random.randint(1, 9999)

    random.seed(st.session_state.seed)

    root, all_nodes, leaves = build_tree(max_depth=tree_depth, max_branch=max_branch)

    # ── Create Users ──
    users = {}
    for i in range(num_users):
        uid = f"U{i+1}"
        home = random.choice(leaves)
        u = User(uid, home)
        u.current_leaf = home
        home.registered_users.append(uid)
        users[uid] = u

    # ── Manual call selection ──
    manual_caller = None
    manual_callee = None
    if manual_mode:
        col_m1, col_m2 = st.sidebar.columns(2)
        user_ids = list(users.keys())
        manual_caller = col_m1.selectbox("Caller", user_ids, index=0)
        manual_callee = col_m2.selectbox("Callee", user_ids, index=min(1, len(user_ids)-1))

    # ── Run Simulation ──
    if manual_mode and manual_caller and manual_callee and manual_caller != manual_callee:
        # just one call
        log, costs_b, costs_o, update_costs, last_path, last_method = run_batch_simulation(
            users, all_nodes, leaves,
            num_calls=0, num_moves=num_moves,
            forwarding_enabled=forwarding_enabled, forwarding_level=forwarding_level,
            replication_enabled=replication_enabled, cmr_threshold=cmr_threshold
        )
        # manual call
        caller = users[manual_caller]
        callee = users[manual_callee]
        caller.calls_made += 1
        callee.calls_received += 1
        path_b, cost_b, _ = route_call_basic(caller.current_leaf, callee.current_leaf, all_nodes)
        if forwarding_enabled:
            path_o, cost_o, method = route_call_with_forwarding(
                caller.current_leaf, callee.current_leaf, all_nodes, callee.uid, forwarding_level)
        elif replication_enabled:
            path_o, cost_o, method = route_call_with_replication(
                caller.current_leaf, callee.current_leaf, all_nodes, callee.uid)
        else:
            path_o, cost_o, method = path_b, cost_b, "Basic LCA"

        costs_b.append(cost_b)
        costs_o.append(cost_o)
        last_path = path_o
        last_method = method
        log.append(f"MANUAL CALL: {manual_caller} → {manual_callee} | Basic: {cost_b} | Optimized: {cost_o} | Method: {method}")
    else:
        log, costs_b, costs_o, update_costs, last_path, last_method = run_batch_simulation(
            users, all_nodes, leaves,
            num_calls=num_calls, num_moves=num_moves,
            forwarding_enabled=forwarding_enabled, forwarding_level=forwarding_level,
            replication_enabled=replication_enabled, cmr_threshold=cmr_threshold
        )

    # ── Display ──
    # Top: Map + Tree side by side
    col1, col2 = st.columns([3, 2])

    with col1:
        highlight_path_names = set(n.name for n in last_path) if last_path else set()

        # gather forwarding edges for visualization
        fwd_edges = []
        for name, node in all_nodes.items():
            for uid, target_name in node.forwarding_pointers.items():
                if target_name in all_nodes:
                    fwd_edges.append((node, all_nodes[target_name]))

        fig_map = draw_us_map_tree(root, all_nodes, users, last_path, fwd_edges)
        st.plotly_chart(fig_map, use_container_width=True)

    with col2:
        fig_tree = draw_logical_tree(root, all_nodes, users, highlight_path_names)
        st.plotly_chart(fig_tree, use_container_width=True)

    # ── Metrics Row ──
    st.subheader("📊 Simulation Results")
    mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
    avg_basic = sum(costs_b) / len(costs_b) if costs_b else 0
    avg_opt = sum(costs_o) / len(costs_o) if costs_o else 0
    avg_update = sum(update_costs) / len(update_costs) if update_costs else 0
    saving_pct = ((avg_basic - avg_opt) / avg_basic * 100) if avg_basic > 0 else 0

    mcol1.metric("Avg Basic Search Cost", f"{avg_basic:.2f}")
    mcol2.metric("Avg Optimized Search Cost", f"{avg_opt:.2f}")
    mcol3.metric("Search Cost Saving", f"{saving_pct:.1f}%")
    mcol4.metric("Avg Update Cost (Replication)", f"{avg_update:.2f}")
    mcol5.metric("Tree Nodes", len(all_nodes))

    # ── Nodes benefiting from forwarding ──
    if forwarding_enabled:
        nodes_with_fwd = sum(1 for n in all_nodes.values() if n.forwarding_pointers)
        st.info(f"🔗 **Forwarding pointers active at {nodes_with_fwd} nodes** (level ≥ {forwarding_level}). "
                f"All calls to users with forwarding pointers at or below this level can short-circuit the LCA lookup.")

    # ── Cost Comparison Chart ──
    st.subheader("📈 Search Cost: Basic vs Optimized (per call)")
    if costs_b:
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Bar(x=list(range(1, len(costs_b)+1)), y=costs_b, name='Basic (LCA)', marker_color='lightcoral'))
        fig_cost.add_trace(go.Bar(x=list(range(1, len(costs_o)+1)), y=costs_o, name='Optimized', marker_color='lightgreen'))
        fig_cost.update_layout(barmode='group', xaxis_title='Call #', yaxis_title='Cost (edges traversed)', height=300, margin=dict(t=30))
        st.plotly_chart(fig_cost, use_container_width=True)

    # ── Update vs Search Cost ──
    if replication_enabled:
        st.subheader("🔄 Update Cost vs Search Cost (Replication Trade-off)")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            fig_tradeoff = go.Figure()
            fig_tradeoff.add_trace(go.Scatter(y=costs_o, mode='lines+markers', name='Search Cost', line=dict(color='green')))
            if update_costs:
                fig_tradeoff.add_trace(go.Scatter(y=update_costs, mode='lines+markers', name='Update Cost', line=dict(color='red')))
            fig_tradeoff.update_layout(height=300, xaxis_title='Event #', yaxis_title='Cost', margin=dict(t=30))
            st.plotly_chart(fig_tradeoff, use_container_width=True)

        with col_r2:
            st.markdown("**Per-User CMR (Call-to-Mobility Ratio)**")
            cmr_data = []
            for u in users.values():
                replicated = "✅" if u.cmr >= cmr_threshold else "❌"
                cmr_data.append({
                    "User": u.uid,
                    "Calls (sent+recv)": u.calls_made + u.calls_received,
                    "Moves": u.moves,
                    "CMR": f"{u.cmr:.2f}" if u.cmr != float('inf') else "∞",
                    "Replicated": replicated,
                    "Location": u.current_leaf.name
                })
            st.dataframe(cmr_data, use_container_width=True)

    # ── User Table ──
    st.subheader("👤 User Status")
    user_table = []
    for u in users.values():
        user_table.append({
            "User ID": u.uid,
            "Home": u.home_leaf.name,
            "Current": u.current_leaf.name,
            "Calls Made": u.calls_made,
            "Calls Received": u.calls_received,
            "Moves": u.moves,
            "CMR": f"{u.cmr:.2f}" if u.cmr != float('inf') else "∞"
        })
    st.dataframe(user_table, use_container_width=True)

    # ── Forwarding Pointer Table ──
    if forwarding_enabled:
        st.subheader("🔗 Forwarding Pointers in Tree")
        fwd_table = []
        for name, node in all_nodes.items():
            for uid, target in node.forwarding_pointers.items():
                fwd_table.append({"Node": name, "Level": node.level, "User": uid, "Points To": target})
        if fwd_table:
            st.dataframe(fwd_table, use_container_width=True)
        else:
            st.info("No forwarding pointers currently set (no user has moved yet, or pointers cleared).")

    # ── Event Log ──
    st.subheader("📝 Event Log")
    log_text = "\n".join(log) if log else "No events yet."
    st.code(log_text, language="text")

    # ── Explanation Panel ──
    with st.expander("📖 How It Works — Technical Explanation"):
        st.markdown("""
### Hierarchical Location Scheme

**Tree Structure:**
- **Level 0 (Root/HLR):** National Home Location Register — knows every user's location (ultimately).
- **Level 1 (Regions):** Northwest, Southwest, Midwest, South, Northeast.
- **Level 2 (States):** Sub-regions within each region.
- **Level 3 (Cities/VLRs):** Visitor Location Registers where users physically register.

**Basic Call Routing (LCA Method):**
1. Start at the caller's current leaf (VLR).
2. Walk UP the tree until reaching the **Lowest Common Ancestor (LCA)** of caller and callee.
3. The LCA has knowledge of the callee's location (or can query downward).
4. Walk DOWN from LCA to the callee's leaf.
5. **Cost** = total edges traversed.

**Forwarding Pointers:**
- When a user moves from leaf X to leaf Y, a pointer is set at X (and nodes up to the configured level) pointing to Y.
- On a subsequent call, instead of going all the way to the LCA, the search can follow the forwarding pointer as soon as it encounters one.
- **Tree Level Based:** Lower forwarding level (e.g., 0 = root) → pointers set higher → more nodes benefit (broader scope) but more pointer storage. Higher level → more localized, fewer nodes benefit.
- **Benefit:** Reduced latency for calls. The savings % shows how much the forwarding pointers reduce search cost on average.

**Replication:**
- Each user has a **Call-to-Mobility Ratio (CMR)** = (calls_sent + calls_received) / moves.
- If CMR ≥ threshold: the user's location is replicated at every node up to the root.
- Searches find replicated info sooner (at lower levels), reducing search cost.
- **Trade-off:** High replication means every move requires updating ALL replicated nodes (high update cost).
- If CMR < threshold: no replication, so moves are cheap but searches go to root.

**Key Observations:**
| Change | Effect |
|--------|--------|
| ↑ Calls, ↓ Moves | CMR rises → replication beneficial → search cost drops |
| ↑ Moves, ↓ Calls | CMR drops → update cost dominates → replication not worth it |
| Enable Forwarding | Search cost reduced, shown in savings % |
| ↑ Forwarding Level | More localized, fewer nodes benefit |
| ↓ Forwarding Level (toward 0) | Broader scope, more nodes benefit |
| ↓ Tree Depth | Fewer levels → lower base cost but less geographic granularity |
| ↑ Branching Factor | Wider tree → different LCA distances |
        """)


if __name__ == "__main__":
    main()
