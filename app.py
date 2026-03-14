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
# BUILD TREE FROM US_HIERARCHY
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
    """
    Baseline: Always go through root (HLR).
    This represents a system without optimization.
    """
    # Path up from caller to root
    path_up = []
    n = caller_leaf
    while n:
        path_up.append(n)
        n = n.parent
    
    # Path down from root to callee
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
    """LCA-based lookup: go up to LCA, then down."""
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
    """
    Check forwarding pointers along the path up from caller.
    """
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
        
        # Path from fwd_node to target_node
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
        
        # Deduplicate consecutive
        deduped = [full_path[0]]
        for p in full_path[1:]:
            if p.name != deduped[-1].name:
                deduped.append(p)
        cost = len(deduped) - 1
        return deduped, cost, f"Forwarding (at L{fwd_node.level}: {fwd_node.name})"

    # Fallback to LCA
    return route_call_lca(caller_leaf, callee_leaf, all_nodes)


def route_call_with_replication(caller_leaf, callee_leaf, root, all_nodes, callee_uid):
    """
    Walk up from caller. If any node has replicated location for callee_uid,
    use that to short-circuit (don't need to go all the way to root).
    """
    n = caller_leaf
    path_up = []
    
    while n:
        path_up.append(n)
        if callee_uid in n.replicated_locations:
            target_name = n.replicated_locations[callee_uid]
            if target_name in all_nodes:
                target_node = all_nodes[target_name]
                
                # Build path down from n to target
                path_down_rev = []
                nn = target_node
                while nn and nn.name != n.name:
                    path_down_rev.append(nn)
                    nn = nn.parent
                path_down = list(reversed(path_down_rev))
                
                full_path = path_up + path_down
                
                # Deduplicate
                deduped = [full_path[0]]
                for p in full_path[1:]:
                    if p.name != deduped[-1].name:
                        deduped.append(p)
                
                return deduped, len(deduped) - 1, f"Replication (at L{n.level}: {n.name})"
        n = n.parent

    # No replication found, go via root
    return route_call_via_root(caller_leaf, callee_leaf, root, all_nodes)


# ─────────────────────────────────────────────────────────────
# FORWARDING POINTERS
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

def update_replication(user, all_nodes, cmr_threshold, replication_level):
    """
    If user CMR >= threshold, replicate location info up to replication_level.
    replication_level: 0 = up to root, 1 = up to region, etc.
    """
    # Clear old
    for node in all_nodes.values():
        if user.uid in node.replicated_locations:
            del node.replicated_locations[user.uid]

    if user.cmr >= cmr_threshold:
        n = user.current_leaf
        while n and n.level >= replication_level:
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
    level_names = {0: 'L0: HLR (Root)', 1: 'L1: Region', 2: 'L2: State', 3: 'L3: City (VLR)'}

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
        height=500, margin=dict(l=0, r=0, t=30, b=0),
        title="  Hierarchical Location Network on US Map",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    return fig


# ─────────────────────────────────────────────────────────────
# DRAW LOGICAL TREE
# ─────────────────────────────────────────────────────────────

def draw_logical_tree(root, all_nodes, users, highlight_path_names=None):
    """Draw tree as a top-down graph using plotly scatter."""
    positions = {}
    _layout_tree(root, positions, x=0, y=0, x_span=100)

    fig = go.Figure()

    # Edges
    for name, node in all_nodes.items():
        if node.parent and name in positions and node.parent.name in positions:
            x0, y0 = positions[node.parent.name]
            x1, y1 = positions[name]
            is_highlight = (highlight_path_names and 
                           node.parent.name in highlight_path_names and 
                           name in highlight_path_names)
            color = 'red' if is_highlight else 'lightgray'
            width = 4 if is_highlight else 1
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0, y1], mode='lines',
                line=dict(color=color, width=width),
                showlegend=False, hoverinfo='none'
            ))

    # Nodes
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
                size=24 if is_highlighted else 16,
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
        height=350, margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, autorange='reversed'),
        title="  Logical Tree Structure (Hierarchical Database)"
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

def run_simulation(users, all_nodes, leaves, root, num_calls, num_moves, 
                   forwarding_enabled, forwarding_level, 
                   replication_enabled, cmr_threshold, replication_level,
                   rng_seed):
    """Run simulation with deterministic RNG."""
    rng = random.Random(rng_seed)
    
    log = []
    costs_baseline = []
    costs_optimized = []
    update_costs = []
    user_list = list(users.values())
    
    # Reset user stats and clear pointers
    for u in user_list:
        u.calls_made = 0
        u.calls_received = 0
        u.moves = 0
    
    for node in all_nodes.values():
        node.forwarding_pointers = {}
        node.replicated_locations = {}

    # Perform moves first
    move_events = []
    for i in range(num_moves):
        u = rng.choice(user_list)
        old_leaf = u.current_leaf
        new_leaf = rng.choice(leaves)
        if new_leaf.name == old_leaf.name:
            continue
        
        u.moves += 1
        
        if forwarding_enabled:
            set_forwarding_pointers(u, old_leaf, new_leaf, forwarding_level)

        # Unregister from old, register at new
        if u.uid in old_leaf.registered_users:
            old_leaf.registered_users = [x for x in old_leaf.registered_users if x != u.uid]
        new_leaf.registered_users.append(u.uid)
        u.current_leaf = new_leaf

        if replication_enabled:
            update_replication(u, all_nodes, cmr_threshold, replication_level)
            uc = compute_update_cost(u, all_nodes)
            update_costs.append(uc)
            log.append(f"  MOVE #{len(move_events)+1}: {u.uid} moved {old_leaf.name} → {new_leaf.name} (Update cost: {uc})")
        else:
            log.append(f"  MOVE #{len(move_events)+1}: {u.uid} moved {old_leaf.name} → {new_leaf.name}")
        
        move_events.append((u.uid, old_leaf.name, new_leaf.name))

    # Perform calls
    last_path = None
    last_method = ""
    call_details = []
    
    for i in range(num_calls):
        caller = rng.choice(user_list)
        callee = rng.choice(user_list)
        if caller.uid == callee.uid:
            continue

        caller.calls_made += 1
        callee.calls_received += 1

        # Baseline cost (via root)
        path_base, cost_base, method_base = route_call_via_root(
            caller.current_leaf, callee.current_leaf, root, all_nodes)
        costs_baseline.append(cost_base)

        # Optimized cost
        if forwarding_enabled:
            path_opt, cost_opt, method_opt = route_call_with_forwarding(
                caller.current_leaf, callee.current_leaf, all_nodes, callee.uid, forwarding_level)
        elif replication_enabled:
            path_opt, cost_opt, method_opt = route_call_with_replication(
                caller.current_leaf, callee.current_leaf, root, all_nodes, callee.uid)
        else:
            path_opt, cost_opt, method_opt = route_call_lca(
                caller.current_leaf, callee.current_leaf, all_nodes)

        costs_optimized.append(cost_opt)
        last_path = path_opt
        last_method = method_opt

        saving = cost_base - cost_opt
        saving_pct = (saving / cost_base * 100) if cost_base > 0 else 0
        
        log.append(f"   CALL #{i+1}: {caller.uid}@{caller.current_leaf.name} → {callee.uid}@{callee.current_leaf.name}")
        log.append(f"   Baseline (via Root): {cost_base} hops | Optimized ({method_opt}): {cost_opt} hops | Saved: {saving} ({saving_pct:.0f}%)")
        
        call_details.append({
            'call_num': i + 1,
            'caller': caller.uid,
            'callee': callee.uid,
            'baseline_cost': cost_base,
            'optimized_cost': cost_opt,
            'method': method_opt,
            'saving': saving
        })

        # Update replication after calls
        if replication_enabled:
            update_replication(caller, all_nodes, cmr_threshold, replication_level)
            update_replication(callee, all_nodes, cmr_threshold, replication_level)

    return {
        'log': log,
        'costs_baseline': costs_baseline,
        'costs_optimized': costs_optimized,
        'update_costs': update_costs,
        'last_path': last_path,
        'last_method': last_method,
        'call_details': call_details,
        'move_count': len(move_events)
    }


# ─────────────────────────────────────────────────────────────
# STREAMLIT APP
# ─────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="Hierarchical Location Scheme", layout="wide")
    st.title("Hierarchical Location Scheme Simulator")
    st.markdown("""
    Simulates call routing, **forwarding pointers**, and **replication** in a hierarchical 
    mobile location management scheme. The tree represents the hierarchy of location databases 
    (HLR → Region → State → City/VLR).
    """)

    # ── Sidebar Controls ──
    st.sidebar.header("Tree Configuration")
    tree_depth = st.sidebar.slider("Tree Depth", 1, 3, 3,
                                    help="1=Regions only, 2=+States, 3=+Cities")
    max_branch = st.sidebar.slider("Max children per node", 2, 6, 4)

    st.sidebar.header("Users")
    num_users = st.sidebar.slider("Number of Users", 2, 20, 6)

    st.sidebar.header("Simulation Parameters")
    num_calls = st.sidebar.slider("Number of Calls", 1, 50, 12)
    num_moves = st.sidebar.slider("Number of User Moves", 0, 30, 4)
    
    st.sidebar.header("🎲 Randomness Control")
    sim_seed = st.sidebar.number_input("Simulation Seed", min_value=1, max_value=9999, value=42,
                                        help="Same seed = same results")
    if st.sidebar.button("Randomize Seed"):
        st.session_state.random_seed = random.randint(1, 9999)
        st.rerun()
    
    if 'random_seed' in st.session_state:
        sim_seed = st.session_state.random_seed

    st.sidebar.header("Forwarding Pointers")
    forwarding_enabled = st.sidebar.checkbox("Enable Forwarding Pointers", value=True)
    forwarding_level = st.sidebar.slider(
        "Forwarding Level", 0, tree_depth, 1,
        help="0=Root (broadest), higher=more localized. Pointers set at this level and below.",
        disabled=not forwarding_enabled)

    st.sidebar.header("Replication")
    replication_enabled = st.sidebar.checkbox("Enable Replication", value=False)
    if replication_enabled and forwarding_enabled:
        st.sidebar.warning("Disable forwarding to see replication effects clearly")
        forwarding_enabled = False
    
    cmr_threshold = st.sidebar.slider(
        "CMR Threshold", 0.5, 10.0, 1.0, 0.5,
        help="Call-to-Mobility Ratio above which location is replicated",
        disabled=not replication_enabled)
    replication_level = st.sidebar.slider(
        "Replication Level", 0, tree_depth, 0,
        help="0=Up to Root, higher=less replication",
        disabled=not replication_enabled)

    # ── Build Tree (deterministic based on parameters) ──
    tree_rng = random.Random(sim_seed)
    root, all_nodes, leaves = build_tree(max_depth=tree_depth, max_branch=max_branch)

    # ── Create Users (deterministic) ──
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
        rng_seed=sim_seed + 1000  # Offset to get different sequence than user creation
    )

    # ── Display Map ──
    highlight_path_names = set(n.name for n in results['last_path']) if results['last_path'] else set()
    
    # Gather forwarding edges
    fwd_edges = []
    for name, node in all_nodes.items():
        for uid, target_name in node.forwarding_pointers.items():
            if target_name in all_nodes:
                fwd_edges.append((node, all_nodes[target_name]))

    fig_map = draw_us_map_tree(root, all_nodes, users, results['last_path'], fwd_edges)
    st.plotly_chart(fig_map, use_container_width=True)

    # ── Tree Below Map ──
    fig_tree = draw_logical_tree(root, all_nodes, users, highlight_path_names)
    st.plotly_chart(fig_tree, use_container_width=True)

    # ── Metrics Row ──
    st.subheader("Performance Metrics")
    
    costs_b = results['costs_baseline']
    costs_o = results['costs_optimized']
    update_costs = results['update_costs']
    
    avg_baseline = sum(costs_b) / len(costs_b) if costs_b else 0
    avg_opt = sum(costs_o) / len(costs_o) if costs_o else 0
    avg_update = sum(update_costs) / len(update_costs) if update_costs else 0
    saving_pct = ((avg_baseline - avg_opt) / avg_baseline * 100) if avg_baseline > 0 else 0
    total_search_cost = sum(costs_o)
    total_update_cost = sum(update_costs)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Avg Baseline Cost", f"{avg_baseline:.2f}", help="Via Root lookup")
    col2.metric("Avg Optimized Cost", f"{avg_opt:.2f}")
    col3.metric("Search Cost Saving", f"{saving_pct:.1f}%", 
                delta=f"-{avg_baseline-avg_opt:.1f} hops" if avg_baseline > avg_opt else None)
    col4.metric("Total Search Cost", f"{total_search_cost}")
    col5.metric("Total Update Cost", f"{total_update_cost}")
    col6.metric("Tree Nodes", len(all_nodes))

    # ── Strategy Summary ──
    strategy_name = "No Optimization"
    if forwarding_enabled:
        strategy_name = f"Forwarding Pointers (Level ≥ {forwarding_level})"
    elif replication_enabled:
        strategy_name = f"Replication (CMR ≥ {cmr_threshold}, Level ≥ {replication_level})"
    
    st.info(f"**Active Strategy:** {strategy_name}")

    # ── Cost Comparison Chart ──
    st.subheader("📈 Search Cost Per Call: Baseline vs Optimized")
    if costs_b:
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Bar(
            x=list(range(1, len(costs_b)+1)), y=costs_b, 
            name='Baseline (via Root)', marker_color='lightcoral'))
        fig_cost.add_trace(go.Bar(
            x=list(range(1, len(costs_o)+1)), y=costs_o, 
            name='Optimized', marker_color='lightgreen'))
        fig_cost.update_layout(
            barmode='group', 
            xaxis_title='Call #', 
            yaxis_title='Cost (hops/edges)', 
            height=300, 
            margin=dict(t=30),
            legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
        )
        st.plotly_chart(fig_cost, use_container_width=True)

    # ── Cumulative Cost Comparison ──
    if len(costs_b) > 1:
        st.subheader("Cumulative Cost Over Time")
        cum_baseline = [sum(costs_b[:i+1]) for i in range(len(costs_b))]
        cum_opt = [sum(costs_o[:i+1]) for i in range(len(costs_o))]
        cum_update = [sum(update_costs[:i+1]) for i in range(len(update_costs))] if update_costs else []
        
        fig_cum = go.Figure()
        fig_cum.add_trace(go.Scatter(
            x=list(range(1, len(cum_baseline)+1)), y=cum_baseline,
            mode='lines+markers', name='Cumulative Baseline Search', line=dict(color='coral')))
        fig_cum.add_trace(go.Scatter(
            x=list(range(1, len(cum_opt)+1)), y=cum_opt,
            mode='lines+markers', name='Cumulative Optimized Search', line=dict(color='green')))
        if cum_update:
            # Extend to match length
            fig_cum.add_trace(go.Scatter(
                x=list(range(1, len(cum_update)+1)), y=cum_update,
                mode='lines+markers', name='Cumulative Update Cost', line=dict(color='orange')))
        
        fig_cum.update_layout(
            xaxis_title='Event #',
            yaxis_title='Cumulative Cost',
            height=300,
            margin=dict(t=30)
        )
        st.plotly_chart(fig_cum, use_container_width=True)

    # ── Replication Details ──
    if replication_enabled:
        st.subheader("📋 Replication & CMR Analysis")
        col_r1, col_r2 = st.columns(2)
        
        with col_r1:
            st.markdown("**Per-User Call-to-Mobility Ratio (CMR)**")
            cmr_data = []
            for u in users.values():
                total_calls = u.calls_made + u.calls_received
                cmr_val = u.cmr
                replicated = "Yes" if cmr_val >= cmr_threshold else "No"
                cmr_display = f"{cmr_val:.2f}" if cmr_val != float('inf') else "∞ (no moves)"
                cmr_data.append({
                    "User": u.uid,
                    "Calls": total_calls,
                    "Moves": u.moves,
                    "CMR": cmr_display,
                    "Replicated": replicated,
                    "Location": u.current_leaf.name
                })
            st.dataframe(cmr_data, use_container_width=True)
        
        with col_r2:
            st.markdown("**Replication Trade-off Explanation**")
            st.markdown(f"""
            - **CMR Threshold:** {cmr_threshold}
            - Users with CMR ≥ {cmr_threshold} have location replicated
            - **High CMR** (many calls, few moves): Replication saves search cost
            - **Low CMR** (few calls, many moves): Update cost dominates
            
            **Current Stats:**
            - Total Search Cost: {total_search_cost}
            - Total Update Cost: {total_update_cost}
            - Net Benefit: {total_search_cost - total_update_cost if replication_enabled else 'N/A'}
            """)

    # ── Forwarding Pointer Details ──
    if forwarding_enabled:
        st.subheader("Forwarding Pointers Analysis")
        
        fwd_table = []
        for name, node in all_nodes.items():
            for uid, target in node.forwarding_pointers.items():
                fwd_table.append({
                    "Node": name, 
                    "Level": node.level, 
                    "User": uid, 
                    "Points To": target
                })
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            if fwd_table:
                st.markdown("**Active Forwarding Pointers**")
                st.dataframe(fwd_table, use_container_width=True)
            else:
                st.info("No forwarding pointers set (no user has moved yet)")
        
        with col_f2:
            st.markdown("**How Forwarding Works**")
            st.markdown(f"""
            When a user moves from node A to node B:
            1. A forwarding pointer is set at A (and ancestors up to level {forwarding_level})
            2. The pointer says: "User X is now at B"
            3. Future calls find the pointer and skip the full tree traversal
            
            **Current Configuration:**
            - Pointers set at levels ≥ {forwarding_level}
            - {len(fwd_table)} active pointers
            - {results['move_count']} moves occurred
            """)

    # ── User Status ──
    st.subheader("User Status")
    user_table = []
    for u in users.values():
        user_table.append({
            "User ID": u.uid,
            "Home": u.home_leaf.name,
            "Current Location": u.current_leaf.name,
            "Calls Made": u.calls_made,
            "Calls Received": u.calls_received,
            "Moves": u.moves,
            "CMR": f"{u.cmr:.2f}" if u.cmr != float('inf') else "∞"
        })
    st.dataframe(user_table, use_container_width=True)

    # ── Event Log ──
    with st.expander("📝 Detailed Event Log"):
        log_text = "\n".join(results['log']) if results['log'] else "No events yet."
        st.code(log_text, language="text")

    # ── Technical Explanation ──
    with st.expander("📖 Technical Explanation"):
        st.markdown("""
### Hierarchical Location Scheme

**Tree Structure:**
| Level | Name | Role |
|-------|------|------|
| 0 | Root (HLR) | Home Location Register - Global database |
| 1 | Region | Regional location server |
| 2 | State | Area-level location server |
| 3 | City (VLR) | Visitor Location Register - Where users connect |

---

### Routing Methods Compared

**1. Baseline (Via Root):**
- Every call goes up to the root, then down to callee
- Cost = depth(caller) + depth(callee)
- Simple but expensive

**2. LCA (Lowest Common Ancestor):**
- Go up only to the common ancestor, then down
- Cost = distance(caller, LCA) + distance(LCA, callee)
- Better than baseline when caller and callee are nearby

**3. Forwarding Pointers:**
- When user moves: A→B, leave pointer at A saying "go to B"
- Calls find pointer before reaching LCA, shortcutting the search
- Best for users who move rarely but receive many calls

**4. Replication:**
- Store user location at multiple tree levels
- Calls find cached info early, avoiding root traversal
- Update cost increases with each move
- Best for high CMR (Call-to-Mobility Ratio)

---

### Key Metrics

| Metric | Formula | Meaning |
|--------|---------|---------|
| CMR | (calls_sent + calls_received) / moves | Higher = replication beneficial |
| Search Cost | Edges traversed to locate user | Lower is better |
| Update Cost | Nodes to update when user moves | Lower is better |
| Total Cost | Search Cost + Update Cost | System efficiency |

---

### When to Use Each Strategy

| Scenario | Best Strategy |
|----------|--------------|
| High mobility, few calls | No optimization (or minimal forwarding) |
| Low mobility, many calls | Replication (high CMR → replicate widely) |
| Users move predictably | Forwarding at intermediate levels |
| Mixed patterns | Combine strategies with CMR threshold |
        """)


if __name__ == "__main__":
    main()
