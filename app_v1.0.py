import streamlit as st
import pandas as pd
import numpy as np
import json
from datetime import datetime

st.set_page_config(layout="wide")
st.title("📊 Decomposition Tree (Delay/KPI/Any Scenario)")

def convert_pandas_to_json_serializable(obj):
    """Convert pandas objects to JSON serializable format"""
    if obj is None:
        return None
    elif isinstance(obj, list):
        return [convert_pandas_to_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_pandas_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, (pd.Series, pd.DataFrame)):
        return obj.to_dict('records')
    elif isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    else:
        # For any other type, try pd.isna() only on scalar values
        try:
            if pd.isna(obj):
                return None
        except (ValueError, TypeError):
            pass
        # Convert to string as fallback
        return str(obj)

def kpi_panel(df, time_comparison="Day"):
    # Create a copy of the dataframe to avoid modifying the original
    df_copy = df.copy()
    if all(col in df.columns for col in ["Status", "Delay_Days"]) and len(df) > 0:
        total_sites = len(df)
        
        # Convert Delay_Days to numeric, handling errors
        df_copy['Delay_Days_Numeric'] = pd.to_numeric(df_copy['Delay_Days'], errors='coerce')
        
        # Calculate status counts based on time comparison method
        if time_comparison == "Week (Monday start)":
            # For week comparison, group by week and calculate status
            if 'Planned_Week_Label' in df_copy.columns and 'Actual_Week_Label' in df_copy.columns:
                # Create week-based status calculation
                df_copy['Week_Status'] = df_copy.apply(lambda row: calculate_week_status(row), axis=1)
                early = len(df_copy[df_copy['Week_Status'] == 'Early'])
                on_time = len(df_copy[df_copy['Week_Status'] == 'On-Time'])
                delayed = len(df_copy[df_copy['Week_Status'] == 'Delayed'])
                pending = len(df_copy[df_copy['Week_Status'] == 'Pending'])
            else:
                # Fallback to original status if week columns not available
                early = len(df_copy[df_copy['Status'] == 'Early'])
                on_time = len(df_copy[df_copy['Status'] == 'On-Time'])
                delayed = len(df_copy[df_copy['Status'] == 'Delayed'])
                pending = len(df_copy[df_copy['Status'] == 'Pending'])
                
        elif time_comparison == "Month":
            # For month comparison, group by month and calculate status
            if 'Planned_Month_Label' in df_copy.columns and 'Actual_Month_Label' in df_copy.columns:
                # Create month-based status calculation
                df_copy['Month_Status'] = df_copy.apply(lambda row: calculate_month_status(row), axis=1)
                early = len(df_copy[df_copy['Month_Status'] == 'Early'])
                on_time = len(df_copy[df_copy['Month_Status'] == 'On-Time'])
                delayed = len(df_copy[df_copy['Month_Status'] == 'Delayed'])
                pending = len(df_copy[df_copy['Month_Status'] == 'Pending'])
            else:
                # Fallback to original status if month columns not available
                early = len(df_copy[df_copy['Status'] == 'Early'])
                on_time = len(df_copy[df_copy['Status'] == 'On-Time'])
                delayed = len(df_copy[df_copy['Status'] == 'Delayed'])
                pending = len(df_copy[df_copy['Status'] == 'Pending'])
        else:
            # Day comparison - use original status
            early = len(df_copy[df_copy['Status'] == 'Early'])
            on_time = len(df_copy[df_copy['Status'] == 'On-Time'])
            delayed = len(df_copy[df_copy['Status'] == 'Delayed'])
            pending = len(df_copy[df_copy['Status'] == 'Pending'])
        
        # Calculate average delay (only for delayed items)
        delayed_data = df_copy.loc[(df_copy['Delay_Days_Numeric'] > 0) & (df_copy['Delay_Days_Numeric'].notna()), 'Delay_Days_Numeric']
        avg_delay = delayed_data.mean() if not delayed_data.empty else 0
        
        # Calculate max delay
        max_delay_data = df_copy.loc[(df_copy['Delay_Days_Numeric'] > 0) & (df_copy['Delay_Days_Numeric'].notna()), 'Delay_Days_Numeric']
        max_delay = max_delay_data.max() if not max_delay_data.empty else 0
        
        # Calculate average early completion (negative delay days)
        early_data = df_copy.loc[(df_copy['Delay_Days_Numeric'] < 0) & (df_copy['Delay_Days_Numeric'].notna()), 'Delay_Days_Numeric']
        avg_early = early_data.mean() if not early_data.empty else 0
        
        # Add time-based insights based on comparison method
        time_insights = ""
        if time_comparison == "Week (Monday start)":
            if 'Planned_Week_Label' in df_copy.columns:
                week_distribution = df_copy['Planned_Week_Label'].value_counts().head(5)
                time_insights = f"\n**Top 5 Planned Weeks:**\n"
                for week, count in week_distribution.items():
                    time_insights += f"• {week}: {count} sites\n"
        elif time_comparison == "Month":
            if 'Planned_Month_Label' in df_copy.columns:
                month_distribution = df_copy['Planned_Month_Label'].value_counts().head(5)
                time_insights = f"\n**Top 5 Planned Months:**\n"
                for month, count in month_distribution.items():
                    time_insights += f"• {month}: {count} sites\n"
        
        st.header(f"🔎 Project KPIs & On-Air Status Summary ({time_comparison})")
        
        # Create conditional display for delay and early metrics
        delay_text = f"**Avg Delay:** {avg_delay:.1f} days" if delayed > 0 else "**Avg Delay:** No delays"
        early_text = f"**Avg Early:** {abs(avg_early):.1f} days early" if early > 0 else "**Avg Early:** No early completions"
        max_delay_text = f"**Max Delay:** {max_delay} days" if delayed > 0 else "**Max Delay:** No delays"
        
        st.info(f"""
        **Total Sites:** {total_sites}  
        🔵 **Early On-Air:** {early}  
        🟢 **On-Time On-Air:** {on_time}  
        🔴 **Delayed On-Air:** {delayed}  
        ⚪ **Pending On-Air:** {pending}  
        {delay_text}  
        {early_text}  
        {max_delay_text}{time_insights}
        """)
    
    return df_copy

def calculate_week_status(row):
    """Calculate status based on week comparison"""
    if pd.isna(row['Planned_Week_Label']) or pd.isna(row['Actual_Week_Label']):
        return 'Pending'
    
    try:
        # Convert week labels to comparable format
        planned_week = str(row['Planned_Week_Label']).split(' ')[0]  # Get "2024-W01" part
        actual_week = str(row['Actual_Week_Label']).split(' ')[0]    # Get "2024-W01" part
        

        
        if planned_week == actual_week:
            return 'On-Time'
        elif actual_week < planned_week:  # Earlier week
            return 'Early'
        else:  # Later week
            return 'Delayed'
    except Exception as e:
        print(f"Error in calculate_week_status: {e}")
        return 'Pending'

def calculate_month_status(row):
    """Calculate status based on month comparison"""
    if pd.isna(row['Planned_Month_Label']) or pd.isna(row['Actual_Month_Label']):
        return 'Pending'
    
    try:
        # Convert month labels to comparable format
        planned_month = str(row['Planned_Month_Label']).split(' ')[0]  # Get "2024-01" part
        actual_month = str(row['Actual_Month_Label']).split(' ')[0]    # Get "2024-01" part
        

        
        if planned_month == actual_month:
            return 'On-Time'
        elif actual_month < planned_month:  # Earlier month
            return 'Early'
        else:  # Later month
            return 'Delayed'
    except Exception as e:
        print(f"Error in calculate_month_status: {e}")
        return 'Pending'

def node_color(status):
    return '#3B82F6'

def build_tree(df, hierarchy, value_col=None, tooltip_cols=None, time_comparison="Day", color_mode="Uniform", uniform_color="#3B82F6", level_colors=None, per_node_colors=None, display_filters=None):
    # Calculate total for percentage calculation
    total_count = len(df)
    
    def add_node(level, parent, df_sub):
        if level >= len(hierarchy):
            return
        col = hierarchy[level]
        for val, group in df_sub.groupby(col):
            val_str = "No Data" if pd.isna(val) else str(val)
            # Visibility-only filtering: skip nodes not selected for display
            if isinstance(display_filters, dict) and col in display_filters:
                allowed_set = display_filters.get(col)
                if isinstance(allowed_set, set) and allowed_set and val_str not in allowed_set:
                    continue
            value = int(group[value_col].sum()) if value_col else int(len(group))
            
            # Calculate percentage
            percentage_raw = (value / total_count) * 100 if total_count > 0 else 0
            # Format percentage: always show as whole number
            percentage = round(percentage_raw)
            
            tooltip_data = {}
            if tooltip_cols:
                for tcol in tooltip_cols:
                    if tcol in group.columns:
                        tdata = group[tcol]
                        vals = list(sorted(set(tdata.astype(str))))
                        tooltip_data[tcol] = ", ".join([v for v in vals if v and v != "nan"])
            # Always include these if present
            for dcol in ["Status","Delay_Days","PIC","Delay_Reason","Planned_OnAir_Date","Actual_OnAir_Date"]:
                if dcol in group.columns and dcol not in (tooltip_data.keys()):
                    vals = list(sorted(set(group[dcol].astype(str))))
                    tooltip_data[dcol] = ", ".join([v for v in vals if v and v != "nan"])
            
            # Add time-based status columns to tooltip based on comparison method
            if time_comparison == "Week (Monday start)" and 'Week_Status' in group.columns:
                vals = list(sorted(set(group['Week_Status'].astype(str))))
                tooltip_data['Week_Status'] = ", ".join([v for v in vals if v and v != "nan"])
            elif time_comparison == "Month" and 'Month_Status' in group.columns:
                vals = list(sorted(set(group['Month_Status'].astype(str))))
                tooltip_data['Month_Status'] = ", ".join([v for v in vals if v and v != "nan"])
            # Safely get the mode status based on time comparison
            status_mode = ""
            if time_comparison == "Week (Monday start)" and 'Week_Status' in group.columns and not group.empty:
                mode_result = group['Week_Status'].mode()
                if len(mode_result) > 0:
                    status_mode = mode_result[0]

            elif time_comparison == "Month" and 'Month_Status' in group.columns and not group.empty:
                mode_result = group['Month_Status'].mode()
                if len(mode_result) > 0:
                    status_mode = mode_result[0]

            elif 'Status' in group.columns and not group.empty:
                mode_result = group['Status'].mode()
                if len(mode_result) > 0:
                    status_mode = mode_result[0]

            
            # Resolve node color
            node_color_value = uniform_color
            if color_mode == "By Level" and isinstance(level_colors, dict) and level in level_colors:
                node_color_value = level_colors.get(level, uniform_color)
            if isinstance(per_node_colors, dict) and (col, val_str) in per_node_colors:
                node_color_value = per_node_colors[(col, val_str)]

            node = {
                "name": f"{col}: {val_str}",
                "children": [],
                "value": value,
                "percentage": percentage,
                "level": level,
                "column": col,
                "node_value": val_str,
                "tooltip_data": tooltip_data,
                "color": node_color_value,
                "raw_data": convert_pandas_to_json_serializable(group.to_dict('records'))
            }
            add_node(level + 1, node, group)
            if not node["children"]:
                node.pop("children")
            parent["children"].append(node)
    root_nodes = []
    
    # Safety check for empty hierarchy
    if not hierarchy:
        return []
    
    col = hierarchy[0]
    for val, group in df.groupby(col):
        val_str = "No Data" if pd.isna(val) else str(val)
        # Visibility-only filtering for root level
        if isinstance(display_filters, dict) and col in display_filters:
            allowed_set = display_filters.get(col)
            if isinstance(allowed_set, set) and allowed_set and val_str not in allowed_set:
                continue
        value = int(group[value_col].sum()) if value_col else int(len(group))
        
        # Calculate percentage for root nodes
        percentage_raw = (value / total_count) * 100 if total_count > 0 else 0
        # Format percentage: always show as whole number
        percentage = round(percentage_raw)
        
        tooltip_data = {}
        if tooltip_cols:
            for tcol in tooltip_cols:
                if tcol in group.columns:
                    tdata = group[tcol]
                    vals = list(sorted(set(tdata.astype(str))))
                    tooltip_data[tcol] = ", ".join([v for v in vals if v and v != "nan"])
        for dcol in ["Status","Delay_Days","PIC","Delay_Reason","Planned_OnAir_Date","Actual_OnAir_Date"]:
            if dcol in group.columns and dcol not in (tooltip_data.keys()):
                vals = list(sorted(set(group[dcol].astype(str))))
                tooltip_data[dcol] = ", ".join([v for v in vals if v and v != "nan"])
        
        # Add time-based status columns to tooltip based on comparison method
        if time_comparison == "Week (Monday start)" and 'Week_Status' in group.columns:
            vals = list(sorted(set(group['Week_Status'].astype(str))))
            tooltip_data['Week_Status'] = ", ".join([v for v in vals if v and v != "nan"])
        elif time_comparison == "Month" and 'Month_Status' in group.columns:
            vals = list(sorted(set(group['Month_Status'].astype(str))))
            tooltip_data['Month_Status'] = ", ".join([v for v in vals if v and v != "nan"])
        
        # Safely get the mode status for root node based on time comparison
        status_mode = ""
        if time_comparison == "Week (Monday start)" and 'Week_Status' in group.columns and not group.empty:
            mode_result = group['Week_Status'].mode()
            if len(mode_result) > 0:
                status_mode = mode_result[0]
        elif time_comparison == "Month" and 'Month_Status' in group.columns and not group.empty:
            mode_result = group['Month_Status'].mode()
            if len(mode_result) > 0:
                status_mode = mode_result[0]
        elif 'Status' in group.columns and not group.empty:
            mode_result = group['Status'].mode()
            if len(mode_result) > 0:
                status_mode = mode_result[0]
        
        # Resolve color for root node
        root_level = 0
        root_color_value = uniform_color
        if color_mode == "By Level" and isinstance(level_colors, dict) and root_level in level_colors:
            root_color_value = level_colors.get(root_level, uniform_color)
        if isinstance(per_node_colors, dict) and (col, val_str) in per_node_colors:
            root_color_value = per_node_colors[(col, val_str)]

        root_node = {
            "name": f"{col}: {val_str}",
            "children": [],
            "value": value,
            "percentage": percentage,
            "level": 0,
            "column": col,
            "node_value": val_str,
            "tooltip_data": tooltip_data,
            "color": root_color_value,
            "raw_data": convert_pandas_to_json_serializable(group.to_dict('records'))
        }
        add_node(1, root_node, group)
        if not root_node["children"]:
            root_node.pop("children")
        root_nodes.append(root_node)
    return root_nodes

st.sidebar.header("🧩 Advanced Configuration")
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    all_cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    
    # Time comparison fixed to Day (options removed)
    time_comparison = "Day"
    
    # Add time-based columns to the dataframe
    if 'Planned_OnAir_Date' in df.columns:
        df['Planned_OnAir_Date'] = pd.to_datetime(df['Planned_OnAir_Date'], errors='coerce')
        if time_comparison == "Week (Monday start)":
            df['Planned_Week'] = df['Planned_OnAir_Date'].dt.strftime('%Y-W%U')
            df['Planned_Week_Label'] = df['Planned_OnAir_Date'].dt.strftime('%Y-W%U (%b %d)')
        elif time_comparison == "Month":
            df['Planned_Month'] = df['Planned_OnAir_Date'].dt.strftime('%Y-%m')
            df['Planned_Month_Label'] = df['Planned_OnAir_Date'].dt.strftime('%Y-%m (%B %Y)')
    
    if 'Actual_OnAir_Date' in df.columns:
        df['Actual_OnAir_Date'] = pd.to_datetime(df['Actual_OnAir_Date'], errors='coerce')
        if time_comparison == "Week (Monday start)":
            df['Actual_Week'] = df['Actual_OnAir_Date'].dt.strftime('%Y-W%U')
            df['Actual_Week_Label'] = df['Actual_OnAir_Date'].dt.strftime('%Y-W%U (%b %d)')
        elif time_comparison == "Month":
            df['Actual_Month'] = df['Actual_OnAir_Date'].dt.strftime('%Y-%m')
            df['Actual_Month_Label'] = df['Actual_OnAir_Date'].dt.strftime('%Y-%m (%B %Y)')
    
    st.sidebar.header("🪜 Hierarchy Configuration")
    
    # Add time-based columns to available options
    time_columns = []
    if time_comparison == "Week (Monday start)":
        if 'Planned_Week_Label' in df.columns:
            time_columns.append('Planned_Week_Label')
        if 'Actual_Week_Label' in df.columns:
            time_columns.append('Actual_Week_Label')
        if 'Week_Status' in df.columns:
            time_columns.append('Week_Status')
    elif time_comparison == "Month":
        if 'Planned_Month_Label' in df.columns:
            time_columns.append('Planned_Month_Label')
        if 'Actual_Month_Label' in df.columns:
            time_columns.append('Actual_Month_Label')
        if 'Month_Status' in df.columns:
            time_columns.append('Month_Status')
    
    # Combine all available columns
    available_cols = all_cols + time_columns
    
    # Use first 6 columns as default, or all columns if less than 6
    default_hierarchy = available_cols[:min(6, len(available_cols))]
    hierarchy = st.sidebar.multiselect(
        "Select hierarchy columns (ordered)",
        available_cols,
        default=default_hierarchy,
        help="⚠️ **Required:** Select at least one column. The order determines the tree structure - first column = root level, second = second level, etc."
    )
    tooltip_cols = st.sidebar.multiselect("Tooltip columns (aggregated for each node)", all_cols, default=[])

    # Visibility filters disabled for minimalist UI
    display_filters = None
    
    # Node style customization
    st.sidebar.header("🎨 Node Style Customization")
    
    # Node shape selection (minimalist: only Default and Star)
    node_shape = st.sidebar.selectbox(
        "Node Shape:",
        ["Default", "Star"],
        help="Minimal options: Default (circle) or Star"
    )
    
    # Node size customization
    node_size = st.sidebar.slider(
        "Node Size:",
        min_value=8,
        max_value=40,
        value=17,
        help="Adjust the size of all nodes in the tree"
    )
    
    # Connection line customization
    st.sidebar.header("🔗 Connection Line Settings")
    line_width = st.sidebar.slider(
        "Line Width:",
        min_value=1,
        max_value=8,
        value=3,
        help="Adjust the thickness of connection lines between nodes"
    )
    
    # Line color: allow preset or custom selection
    line_color_presets = {
        "Default Gray": "#9CA3AF",
        "Slate": "#64748B",
        "Black": "#111827",
        "Blue": "#3B82F6",
        "Green": "#10B981",
        "Amber": "#F59E0B",
        "Red": "#EF4444",
        "Violet": "#8B5CF6",
        "Cyan": "#06B6D4"
    }
    line_color_source = st.sidebar.selectbox(
        "Line Color Source:",
        ["Preset", "Custom"],
        index=0,
        help="Use a preset color or pick a custom RGB/HEX"
    )
    if line_color_source == "Preset":
        chosen_line_preset = st.sidebar.selectbox("Line Color (preset):", list(line_color_presets.keys()), index=0)
        line_color = line_color_presets[chosen_line_preset]
    else:
        line_color = st.sidebar.color_picker(
            "Line Color:",
            value="#9CA3AF",
            help="Choose the color for connection lines"
        )
    
    line_opacity = st.sidebar.slider(
        "Line Opacity:",
        min_value=0.1,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="Adjust the transparency of connection lines"
    )
    
    # Font size customization
    st.sidebar.header("📝 Label Font Settings")
    font_size = st.sidebar.slider(
        "Font Size:",
        min_value=10,
        max_value=20,
        value=13,
        help="Adjust the font size of node labels"
    )
    
    font_weight = st.sidebar.selectbox(
        "Font Weight:",
        ["400", "500", "600", "700", "800"],
        index=2,  # Default to 600
        help="Choose the font weight for labels"
    )
    
    # Presentation style
    style_theme = st.sidebar.selectbox(
        "Style theme",
        ["Standard", "Mind Map"],
        index=0,
        help="Mind Map adds rounded outlines and presentation styling"
    )
    show_group_outlines = False
    group_outline_level = 0
    minimal_labels = False
    outline_opacity = 0.25
    if style_theme == "Mind Map":
        show_group_outlines = st.sidebar.checkbox("Show dashed group outlines", value=False)
        group_outline_level = st.sidebar.slider(
            "Group outline level",
            min_value=0,
            max_value=max(0, len(hierarchy) - 1),
            value=min(2, max(0, len(hierarchy) - 1)),
            help="Draw a rounded dashed box around each subtree at this depth"
        )
        minimal_labels = st.sidebar.checkbox("Minimal labels (name only)", value=False, help="Hide values/percentages on nodes for a clean look")
        outline_opacity = st.sidebar.slider(
            "Outline opacity",
            min_value=0.10,
            max_value=0.50,
            value=0.25,
            step=0.05,
            help="Subtle outlines keep the style professional and minimalist"
        )
    
    # Label content mode
    label_display_mode = st.sidebar.selectbox(
        "Data label content",
        ["Value + Percentage", "Value only", "Percentage only"],
        index=0,
        help="Choose what to append to node labels"
    )
    if label_display_mode == "Value only":
        label_mode_key = "value_only"
    elif label_display_mode == "Percentage only":
        label_mode_key = "percentage_only"
    else:
        label_mode_key = "value_percentage"

    # Node color configuration
    st.sidebar.header("🎨 Node Colors")
    color_mode = st.sidebar.selectbox(
        "Color mode",
        ["Uniform", "By Level", "Per Node (UI)", "Per Node (CSV)"],
        index=0,
        help="Uniform = one color; By Level = per-depth; Per Node (UI/CSV) = specific nodes"
    )
    uniform_node_color = "#3B82F6"
    level_colors = None
    per_node_colors = None
    if color_mode == "Uniform":
        # Single-color presets plus custom picker
        single_color_presets = {
            "Default Blue": "#3B82F6",
            "Green": "#10B981",
            "Amber": "#F59E0B",
            "Red": "#EF4444",
            "Violet": "#8B5CF6",
            "Teal": "#14B8A6",
            "Orange": "#F97316",
            "Cyan": "#06B6D4",
            "Slate": "#64748B",
            "Black": "#111827"
        }
        uniform_color_source = st.sidebar.selectbox("Uniform color source:", ["Preset", "Custom"], index=0)
        if uniform_color_source == "Preset":
            chosen_uniform_preset = st.sidebar.selectbox("Uniform Color (preset):", list(single_color_presets.keys()), index=0)
            uniform_node_color = single_color_presets[chosen_uniform_preset]
        else:
            uniform_node_color = st.sidebar.color_picker(
                "Node Color",
                value="#3B82F6",
                help="Set the color for all nodes"
            )
    elif color_mode == "By Level":
        # Preset palettes + optional customization
        level_palette_presets = {
            "Category10 (d3)": [
                "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
            ],
            "Tableau10": [
                "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
                "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"
            ],
            "Okabe-Ito (colorblind-safe)": [
                "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7",
                "#F0E442", "#56B4E9", "#000000"
            ],
            "Set2": ["#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3", "#A6D854", "#FFD92F", "#E5C494", "#B3B3B3"],
            "Pastel1": ["#FBB4AE", "#B3CDE3", "#CCEBC5", "#DECBE4", "#FED9A6", "#FFFFCC", "#E5D8BD", "#FDDAEC", "#F2F2F2"]
        }
        palette_name = st.sidebar.selectbox("Level palette (preset):", list(level_palette_presets.keys()), index=0)
        customize_levels = st.sidebar.checkbox("Customize palette colors", value=False)
        max_levels = len(hierarchy)
        level_colors = {}
        base_palette = level_palette_presets[palette_name]
        if not customize_levels:
            for lvl in range(max_levels):
                level_colors[lvl] = base_palette[lvl % len(base_palette)]
        else:
            for lvl in range(max_levels):
                default_color = base_palette[lvl % len(base_palette)]
                level_colors[lvl] = st.sidebar.color_picker(
                    f"Level {lvl} Color",
                    value=default_color
                )
    elif color_mode == "Per Node (UI)":
        # Interactive per-node overrides with session persistence
        if "per_node_ui_colors" not in st.session_state:
            st.session_state["per_node_ui_colors"] = {}
        per_node_colors = dict(st.session_state["per_node_ui_colors"])  # copy
        if hierarchy:
            selected_override_column = st.sidebar.selectbox("Override column", hierarchy)
            unique_vals = (
                df[selected_override_column]
                .astype(object)
                .where(pd.notna(df[selected_override_column]), None)
            )
            # Convert to strings with No Data for None/NaN
            normalized_vals = []
            for v in unique_vals.astype(str).unique().tolist():
                normalized_vals.append("No Data" if v in ["None", "nan", "NaT"] else v)
            normalized_vals = sorted(set(normalized_vals))
            st.sidebar.write("Set colors for each value:")
            for nval in normalized_vals:
                key = f"color__{selected_override_column}__{nval}"
                default_color = per_node_colors.get((selected_override_column, nval), "#3B82F6")
                chosen = st.sidebar.color_picker(f"{selected_override_column} = {nval}", value=default_color, key=key)
                per_node_colors[(selected_override_column, nval)] = chosen
            if st.sidebar.button("Save overrides", use_container_width=True):
                st.session_state["per_node_ui_colors"] = per_node_colors
            if st.sidebar.button("Reset overrides", use_container_width=True):
                st.session_state["per_node_ui_colors"] = {}
                per_node_colors = {}
        else:
            st.sidebar.info("Select hierarchy columns first.")
    else:  # Per Node (CSV)
        st.sidebar.markdown("Upload a CSV to override colors per node.")
        st.sidebar.markdown("Columns: 'column' (hierarchy), 'node_value' (value), 'color' (hex)")
        per_node_file = st.sidebar.file_uploader("Per-node color CSV", type=["csv"])
        if per_node_file is not None:
            try:
                per_df = pd.read_csv(per_node_file)
                per_node_colors = {}
                for _, row in per_df.iterrows():
                    colname = str(row.get("column", "")).strip()
                    nval = str(row.get("node_value", "")).strip()
                    colhex = str(row.get("color", "")).strip()
                    if colname and nval and colhex:
                        per_node_colors[(colname, nval)] = colhex
            except Exception as e:
                st.sidebar.error(f"Failed to parse per-node color CSV: {e}")

    # Node order configuration
    st.sidebar.header("↕ Node Order")
    order_mode = st.sidebar.selectbox(
        "Initial sort",
        ["Custom (as-is)", "Name A→Z", "Name Z→A", "Value Asc", "Value Desc"],
        index=0
    )
    enable_drag_reorder = st.sidebar.checkbox("Enable drag & drop reorder", True)
    
    agg_method = st.sidebar.selectbox("Aggregation method", ["Count", "Sum", "Average"])
    value_col = None
    if agg_method == "Count":
        df["__value__"] = 1
        value_col = "__value__"
    elif agg_method in ["Sum", "Average"]:
        value_col = st.sidebar.selectbox("Select value column", numeric_cols if numeric_cols else all_cols, index=0)
        df["__value__"] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
        value_col = "__value__"

    # KPI panel removed

    # Check if hierarchy is empty and provide user guidance
    if not hierarchy:
        st.error("⚠️ **No columns selected for hierarchy!**")
        st.info("""
        **Please select at least one column** from the "Select hierarchy columns" dropdown in the sidebar.
        
        💡 **Tip:** The hierarchy determines how your data will be organized in the tree structure.
        - First column = Root level
        - Second column = Second level
        - And so on...
        
        **Recommended:** Start with your main categories (e.g., Project, Status, Region, etc.)
        """)
        st.stop()
    
    # Update hierarchy to use time-based status columns if needed
    updated_hierarchy = []
    for col in hierarchy:
        if col == "Status" and time_comparison == "Week (Monday start)" and 'Week_Status' in df.columns:
            updated_hierarchy.append("Week_Status")
        elif col == "Status" and time_comparison == "Month" and 'Month_Status' in df.columns:
            updated_hierarchy.append("Month_Status")
        else:
            updated_hierarchy.append(col)
    
    tree_data = build_tree(
        df,
        updated_hierarchy,
        value_col,
        tooltip_cols,
        time_comparison,
        color_mode=color_mode,
        uniform_color=uniform_node_color,
        level_colors=level_colors,
        per_node_colors=per_node_colors,
        display_filters=display_filters
    )
    if tree_data and len(tree_data) > 0:
        if len(tree_data) == 1:
            d3_tree_data = tree_data[0]
        else:
            d3_tree_data = {
                "name": "Root",
                "children": tree_data,
                "level": -1,
                "value": sum(node.get("value", 0) for node in tree_data),
                "tooltip_data": {},
                "color": "#3B82F6",
                "raw_data": convert_pandas_to_json_serializable(df.to_dict('records'))
            }
    else:
        d3_tree_data = {"name": "No Data", "children": [], "level": 0, "value": 0, "tooltip_data": {}, "color": "#9CA3AF", "raw_data": []}

    # Convert the entire tree data to JSON serializable format
    try:
        d3_tree_data_serializable = convert_pandas_to_json_serializable(d3_tree_data)
        tree_data_json = json.dumps(d3_tree_data_serializable, ensure_ascii=False).replace('</', r'<\/')
    except Exception as e:
        st.error(f"Error converting data to JSON: {str(e)}")
        # Fallback to a simple structure without raw_data
        d3_tree_data_simple = {
            "name": d3_tree_data.get("name", "Error"),
            "children": d3_tree_data.get("children", []),
            "level": d3_tree_data.get("level", 0),
            "value": d3_tree_data.get("value", 0),
            "tooltip_data": d3_tree_data.get("tooltip_data", {}),
            "color": d3_tree_data.get("color", "#9CA3AF"),
            "raw_data": []
        }
        tree_data_json = json.dumps(d3_tree_data_simple, ensure_ascii=False).replace('</', r'<\/')

    # Export quality settings
    st.sidebar.header("🖼️ Export Settings")
    export_png_scale = st.sidebar.slider(
        "PNG export quality (scale)",
        min_value=1,
        max_value=6,
        value=3,
        help="Increase for sharper images (and larger files)"
    )

    d3_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <script src="https://d3js.org/d3.v7.min.js"></script>
      <script>
        // Node shape and size configuration
        const nodeShape = "{node_shape}";
        const nodeSize = {node_size};
        
        // Connection line configuration
        const lineWidth = {line_width};
        const lineColor = "{line_color}";
        const lineOpacity = {line_opacity};
        
        // Font configuration
        const fontSize = {font_size};
        const fontWeight = "{font_weight}";
        
        // Style/theme
        const styleMode = "{style_theme}"; // Standard | Mind Map
        const showGroupOutlines = {str(show_group_outlines).lower()};
        const groupOutlineLevel = {group_outline_level};
        const minimalLabels = {str(minimal_labels).lower()};
        const outlineOpacity = {outline_opacity};
        
        // Ordering and interactions
        const orderMode = "{order_mode}";
        const enableDragReorder = {str(enable_drag_reorder).lower()};
        let manualOrder = false;
        let dragActive = false;

        // Label display mode from sidebar
        const labelMode = "{label_mode_key}"; // value_only | percentage_only | value_percentage
        // Export quality scale from sidebar
        const exportScale = {export_png_scale};

        // Helpers
        function roundedRectPath(x, y, width, height, radius) {{
          const r = Math.min(radius, width / 2, height / 2);
          return "M " + (x + r) + "," + y
               + " H " + (x + width - r)
               + " A " + r + "," + r + " 0 0 1 " + (x + width) + "," + (y + r)
               + " V " + (y + height - r)
               + " A " + r + "," + r + " 0 0 1 " + (x + width - r) + "," + (y + height)
               + " H " + (x + r)
               + " A " + r + "," + r + " 0 0 1 " + x + "," + (y + height - r)
               + " V " + (y + r)
               + " A " + r + "," + r + " 0 0 1 " + (x + r) + "," + y
               + " Z";
        }}

        function formatLabel(d) {{
          const name = d.data.name || "";
          const hasValue = d.data.value !== undefined && d.data.value !== null;
          const hasPct = d.data.percentage !== undefined && d.data.percentage !== null;
          if (styleMode === "Mind Map" && minimalLabels) {{
            return name;
          }}
          if (labelMode === "value_only") {{
            return hasValue ? `${{name}} (${{d.data.value}})` : name;
          }} else if (labelMode === "percentage_only") {{
            return hasPct ? `${{name}} (${{d.data.percentage}}%)` : name;
          }}
          // default value + percentage
          return hasValue && hasPct ? `${{name}} (${{d.data.value}}, ${{d.data.percentage}}%)` : name;
        }}

        function compareNodes(a, b) {{
          const nameA = (a.data.name || "").toString().toLowerCase();
          const nameB = (b.data.name || "").toString().toLowerCase();
          const valA = (a.data.value || 0);
          const valB = (b.data.value || 0);
          if (orderMode === "Name A→Z") return nameA.localeCompare(nameB);
          if (orderMode === "Name Z→A") return nameB.localeCompare(nameA);
          if (orderMode === "Value Asc") return valA - valB;
          if (orderMode === "Value Desc") return valB - valA;
          return 0; // Custom (as-is)
        }}

        function sortArray(arr) {{
          if (!arr) return;
          arr.sort(compareNodes);
          arr.forEach(child => {{
            if (child.children) sortArray(child.children);
            if (child._children) sortArray(child._children);
          }});
        }}

        function applyInitialSort(root) {{
          if (orderMode === "Custom (as-is)" || manualOrder) return;
          sortArray(root.children);
          sortArray(root._children);
        }}
        
        // Node shape functions
        function createNodeShape(selection, size) {{
          switch(nodeShape) {{
            case "Circle":
              selection.append("circle")
                .attr("r", size)
                .attr("fill", d => d.data.color || "#CBD5E1")
                .attr("stroke", "#fff")
                .attr("stroke-width", 3);
              break;
            case "Square":
              selection.append("rect")
                .attr("width", size * 2)
                .attr("height", size * 2)
                .attr("x", -size)
                .attr("y", -size)
                .attr("fill", d => d.data.color || "#CBD5E1")
                .attr("stroke", "#fff")
                .attr("stroke-width", 3)
                .attr("rx", 2);
              break;
            case "Diamond":
              selection.append("polygon")
                .attr("points", d => {{
                  const s = size;
                  return `0,-${{s}} ${{s}},0 0,${{s}} -${{s}},0`;
                }})
                .attr("fill", d => d.data.color || "#CBD5E1")
                .attr("stroke", "#fff")
                .attr("stroke-width", 3);
              break;
            case "Triangle":
              selection.append("polygon")
                .attr("points", d => {{
                  const s = size;
                  return `0,-${{s}} -${{s}},${{s}} ${{s}},${{s}}`;
                }})
                .attr("fill", d => d.data.color || "#CBD5E1")
                .attr("stroke", "#fff")
                .attr("stroke-width", 3);
              break;
            case "Star":
              selection.append("path")
                .attr("d", d => {{
                  const s = size;
                  const points = [];
                  for (let i = 0; i < 10; i++) {{
                    const angle = (i * Math.PI) / 5;
                    const r = i % 2 === 0 ? s : s * 0.5;
                    points.push(`${{Math.cos(angle) * r}},${{Math.sin(angle) * r}}`);
                  }}
                  return `M ${{points.join(' L ')}} Z`;
                }})
                .attr("fill", d => d.data.color || "#CBD5E1")
                .attr("stroke", "#fff")
                .attr("stroke-width", 3);
              break;
            case "Hexagon":
              selection.append("polygon")
                .attr("points", d => {{
                  const s = size;
                  const points = [];
                  for (let i = 0; i < 6; i++) {{
                    const angle = (i * Math.PI) / 3;
                    points.push(`${{Math.cos(angle) * s}},${{Math.sin(angle) * s}}`);
                  }}
                  return points.join(' ');
                }})
                .attr("fill", d => d.data.color || "#CBD5E1")
                .attr("stroke", "#fff")
                .attr("stroke-width", 3);
              break;
            case "Cross":
              selection.append("g")
                .each(function(d) {{
                  const g = d3.select(this);
                  const s = size;
                  // Vertical line
                  g.append("rect")
                    .attr("x", -2)
                    .attr("y", -s)
                    .attr("width", 4)
                    .attr("height", s * 2)
                    .attr("fill", d.data.color || "#CBD5E1")
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 3);
                  // Horizontal line
                  g.append("rect")
                    .attr("x", -s)
                    .attr("y", -2)
                    .attr("width", s * 2)
                    .attr("height", 4)
                    .attr("fill", d.data.color || "#CBD5E1")
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 3);
                }});
              break;
            case "Plus":
              selection.append("g")
                .each(function(d) {{
                  const g = d3.select(this);
                  const s = size;
                  // Vertical line
                  g.append("rect")
                    .attr("x", -2)
                    .attr("y", -s)
                    .attr("width", 4)
                    .attr("height", s * 2)
                    .attr("fill", d.data.color || "#CBD5E1")
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 3);
                  // Horizontal line
                  g.append("rect")
                    .attr("x", -s)
                    .attr("y", -2)
                    .attr("width", s * 2)
                    .attr("height", 4)
                    .attr("fill", d.data.color || "#CBD5E1")
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 3);
                }});
              break;
            default:
              selection.append("circle")
                .attr("r", size)
                .attr("fill", d => d.data.color || "#CBD5E1")
                .attr("stroke", "#fff")
                .attr("stroke-width", 3);
          }}
        }}
      </script>
      <style>
      .node circle {{ stroke: #fff; stroke-width: 3px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.10)); }}
      .node text {{ font-family: Calibri, Arial, sans-serif; font-size: {font_size}px; font-weight: {font_weight}; fill: #111; }}
      .link {{ fill: none; stroke: {line_color}; stroke-width: {line_width}px; stroke-opacity: {line_opacity}; }}
      .tooltip {{
        position: absolute; background: #1e293b; color: #fff;
        padding: 12px 16px; border-radius: 8px; font-size: 13px; font-family: Calibri, Arial, sans-serif;
        pointer-events: none; z-index: 1000; max-width: 320px; line-height: 1.5; box-shadow: 0 8px 32px rgba(0,0,0,0.10);
      }}
      .region-outline {{
        fill: none; stroke: #94A3B8; stroke-width: 2.5px; stroke-dasharray: 8 6;
      }}
      .controls {{
        position: absolute; top: 10px; left: 10px; z-index: 1001;
        background: rgba(255,255,255,0.95); padding: 10px; border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-family: Calibri, Arial, sans-serif;
      }}
      .control-btn {{
        background: #3B82F6; color: white; border: none; padding: 8px 12px;
        margin: 2px; border-radius: 4px; cursor: pointer; font-size: 12px;
        transition: background 0.2s;
      }}
      .control-btn:hover {{ background: #2563EB; }}
      .control-btn:active {{ background: #1D4ED8; }}
      .zoom-info {{
        position: absolute; top: 10px; right: 10px; z-index: 1001;
        background: rgba(255,255,255,0.95); padding: 8px 12px; border-radius: 6px;
        font-size: 12px; font-family: Calibri, Arial, sans-serif;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      }}
      .download-panel {{
        position: absolute; bottom: 10px; left: 10px; z-index: 1001;
        background: rgba(255,255,255,0.95); padding: 12px; border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-family: Calibri, Arial, sans-serif;
        display: flex; flex-direction: column; gap: 8px;
      }}
      .download-btn {{
        background: #10B981; color: white; border: none; padding: 8px 12px;
        border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600;
        transition: background 0.2s; display: flex; align-items: center; gap: 6px;
      }}
      .download-btn:hover {{ background: #059669; }}
      .download-btn:active {{ background: #047857; }}
      .download-btn.svg {{ background: #8B5CF6; }}
      .download-btn.svg:hover {{ background: #7C3AED; }}
      .download-btn.svg:active {{ background: #6D28D9; }}
      .download-btn.transparent {{ background: #F59E0B; }}
      .download-btn.transparent:hover {{ background: #D97706; }}
      .download-btn.transparent:active {{ background: #B45309; }}
      .context-menu {{
        position: absolute; background: #1e293b; color: #fff;
        padding: 8px 0; border-radius: 8px; font-size: 13px; font-family: Calibri, Arial, sans-serif;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15); z-index: 1002; min-width: 180px;
        display: none;
      }}
      .context-menu-item {{
        padding: 8px 16px; cursor: pointer; transition: background 0.2s;
        display: flex; align-items: center; gap: 8px;
      }}
      .context-menu-item:hover {{ background: #374151; }}
      .context-menu-separator {{
        height: 1px; background: #4B5563; margin: 4px 0;
      }}
      .node-data-panel {{
        position: absolute; top: 10px; left: 50%; transform: translateX(-50%); z-index: 1001;
        background: rgba(255,255,255,0.95); padding: 12px; border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-family: Calibri, Arial, sans-serif;
        display: none; max-width: 400px;
      }}
      .node-data-panel h4 {{ margin: 0 0 8px 0; color: #374151; font-size: 14px; }}
      .node-data-panel .data-item {{ margin: 4px 0; font-size: 12px; }}
      .node-data-panel .data-label {{ font-weight: 600; color: #6B7280; }}
      .node-data-panel .data-value {{ color: #111; }}
      </style>
    </head>
    <body>
    <div id="tree"></div>
    <div id="contextMenu" class="context-menu">
      <div class="context-menu-item" onclick="downloadNodeData()">
        📊 Download Node Data (CSV)
      </div>
      <div class="context-menu-item" onclick="downloadNodeDataExcel()">
        📈 Download Node Data (Excel)
      </div>
      <div class="context-menu-separator"></div>
      <div class="context-menu-item" onclick="showNodeDetails()">
        🔍 Show Node Details
      </div>
      <div class="context-menu-item" onclick="downloadNodeTree()">
        🌳 Download Node Tree (JSON)
      </div>
    </div>
    <div id="nodeDataPanel" class="node-data-panel">
      <h4>📋 Node Information</h4>
      <div id="nodeDataContent"></div>
    </div>
    <div class="controls">
      <button class="control-btn" onclick="expandAll()">🔽 Expand All</button>
      <button class="control-btn" onclick="collapseAll()">🔼 Collapse All</button>
      <button class="control-btn" onclick="resetZoom()">🎯 Reset View</button>
      <div style="margin-top: 8px; font-size: 11px; color: #666;">
        <div>🖱️ Drag to pan</div>
        <div>🔍 Scroll to zoom</div>
        <div>👆 Click nodes to expand/collapse</div>
        <div>🖱️ Right-click nodes for data download</div>
      </div>
    </div>
    <div class="zoom-info" id="zoomInfo">Zoom: 100%</div>
    <div class="download-panel">
      <div style="font-size: 11px; font-weight: 600; color: #374151; margin-bottom: 4px;">📥 Download Chart</div>
      <button class="download-btn" onclick="downloadPNG()">🖼️ PNG (Complete Tree)</button>
      <button class="download-btn transparent" onclick="downloadPNGTransparent()">🖼️ PNG (White Bg)</button>
      <button class="download-btn svg" onclick="downloadSVG()">📐 SVG (Complete Tree)</button>
      <button class="download-btn svg transparent" onclick="downloadSVGTransparent()">📐 SVG (White Bg)</button>
      <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #E5E7EB;">
        <div style="font-size: 10px; color: #6B7280; margin-bottom: 4px;">Current View Export:</div>
        <button class="download-btn" onclick="downloadCurrentViewPNG()" style="font-size: 11px; padding: 6px 10px;">🖼️ PNG (Current View)</button>
        <button class="download-btn svg" onclick="downloadCurrentViewSVG()" style="font-size: 11px; padding: 6px 10px;">📐 SVG (Current View)</button>
      </div>
    </div>
    <script>
    const data = {tree_data_json};
    const width = 1100, height = 800, dx = 44, dy = 220;
    const tree = d3.tree().nodeSize([dx, dy]);
    const diagonal = d3.linkHorizontal().x(d => d.y).y(d => d.x);
    const root = d3.hierarchy(data);
    
    // Global variables for context menu
    let selectedNode = null;
    let contextMenu = null;
    let nodeDataPanel = null;
    
    // Initialize all nodes with _children for expand/collapse
    root.descendants().forEach(d => {{
      if (d.children) d._children = d.children;
      if (d.depth > 1) d.children = null; // Start collapsed for deeper levels
    }});
    
    // Apply initial sorting if requested
    applyInitialSort(root);
    
    const svg = d3.select("#tree").append("svg")
      .attr("width", width).attr("height", height)
      .attr("viewBox", [0, 0, width, height])
      .style("font", "15px Calibri");
    
    // Add zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.1, 3])
      .on("zoom", (event) => {{
        g.attr("transform", event.transform);
        updateZoomInfo(event.transform.k);
      }});
    
    svg.call(zoom);
    
    // Center the tree by default
    const g = svg.append("g");
    const gRegion = g.append("g").attr("class", "regions");
    const gLink = g.append("g").attr("stroke", lineColor).attr("stroke-opacity", lineOpacity);
    const gNode = g.append("g").attr("cursor", "pointer");
    // Ensure proper layer order: regions at bottom, links middle, nodes top
    gRegion.lower();
    gLink.raise();
    gNode.raise();
    const tooltip = d3.select("body").append("div").attr("class", "tooltip").style("opacity", 0);
    
    function updateZoomInfo(scale) {{
      document.getElementById("zoomInfo").textContent = `Zoom: ${{Math.round(scale * 100)}}%`;
    }}
    
    function expandAll() {{
      // Create a fresh complete tree from the original data
      const completeRoot = d3.hierarchy(data);
      
      // Recursively restore all children to the current root
      function restoreChildren(currentNode, completeNode) {{
        if (completeNode.children) {{
          currentNode._children = completeNode.children;
          currentNode.children = completeNode.children;
          // Ensure parent pointers are correct for layout/link generation
          currentNode.children.forEach(c => {{ c.parent = currentNode; }});
          
          // Recursively restore children for each child node
          currentNode.children.forEach((child, index) => {{
            if (completeNode.children[index]) {{
              restoreChildren(child, completeNode.children[index]);
            }}
          }});
        }}
      }}
      
      // Restore the complete structure
      restoreChildren(root, completeRoot);
      
      update(root);
      // Center the expanded tree
      setTimeout(() => {{
        const nodes = root.descendants();
        if (nodes.length > 0) {{
          const minX = d3.min(nodes, d => d.x);
          const maxX = d3.max(nodes, d => d.x);
          const minY = d3.min(nodes, d => d.y);
          const maxY = d3.max(nodes, d => d.y);
          const treeWidth = maxY - minY;
          const treeHeight = maxX - minX;
          const centerX = width / 2 - (minY + treeWidth / 2);
          const centerY = height / 2 - (minX + treeHeight / 2);
          svg.transition().duration(750).call(
            zoom.transform,
            d3.zoomIdentity.translate(centerX, centerY).scale(1)
          );
        }}
      }}, 100);
    }}
    
    function collapseAll() {{
      root.descendants().forEach(d => {{
        if (d.children) {{
          d._children = d.children;
          d.children = null;
        }}
      }});
      update(root);
      // Center the collapsed tree
      setTimeout(() => {{
        const nodes = root.descendants();
        if (nodes.length > 0) {{
          const minX = d3.min(nodes, d => d.x);
          const maxX = d3.max(nodes, d => d.x);
          const minY = d3.min(nodes, d => d.y);
          const maxY = d3.max(nodes, d => d.y);
          const treeWidth = maxY - minY;
          const treeHeight = maxX - minX;
          const centerX = width / 2 - (minY + treeWidth / 2);
          const centerY = height / 2 - (minX + treeHeight / 2);
          svg.transition().duration(750).call(
            zoom.transform,
            d3.zoomIdentity.translate(centerX, centerY).scale(1)
          );
        }}
      }}, 100);
    }}
    
    function resetZoom() {{
      const nodes = root.descendants();
      if (nodes.length > 0) {{
        const minX = d3.min(nodes, d => d.x);
        const maxX = d3.max(nodes, d => d.x);
        const minY = d3.min(nodes, d => d.y);
        const maxY = d3.max(nodes, d => d.y);
        const treeWidth = maxY - minY;
        const treeHeight = maxX - minX;
        const centerX = width / 2 - (minY + treeWidth / 2);
        const centerY = height / 2 - (minX + treeHeight / 2);
        svg.transition().duration(750).call(
          zoom.transform,
          d3.zoomIdentity.translate(centerX, centerY).scale(1)
        );
      }}
    }}
    
    function downloadPNG() {{
      // Create a complete tree with all nodes expanded for export
      const exportRoot = d3.hierarchy(data);
      exportRoot.descendants().forEach(d => {{
        if (d._children) d.children = d._children;
      }});
      
      // Calculate tree layout for export
      const exportTree = d3.tree().nodeSize([dx, dy]);
      exportTree(exportRoot);
      
      const nodes = exportRoot.descendants();
      if (nodes.length === 0) return;
      
      // Compute precise bounds including node shapes and labels
      const measure = document.createElement('canvas').getContext('2d');
      measure.font = fontWeight + ' ' + fontSize + 'px Calibri, Arial, sans-serif';
      let minXBound = Infinity, maxXBound = -Infinity, minYBound = Infinity, maxYBound = -Infinity;
      nodes.forEach(d => {{
        const label = formatLabel(d);
        const textWidth = measure.measureText(label).width;
        const halfText = textWidth / 2;
        const top = d.x - (nodeSize + fontSize + 8);
        const bottom = d.x + (nodeSize + 8);
        const left = d.y - Math.max(halfText, nodeSize);
        const right = d.y + Math.max(halfText, nodeSize);
        if (top < minXBound) minXBound = top;
        if (bottom > maxXBound) maxXBound = bottom;
        if (left < minYBound) minYBound = left;
        if (right > maxYBound) maxYBound = right;
      }});
      const basePadding = 40;
      const outlineExtraPadding = (styleMode === "Mind Map" && showGroupOutlines) ? Math.ceil(nodeSize * 3) : 0;
      const padding = basePadding + outlineExtraPadding;
      const treeWidth = Math.ceil((maxYBound - minYBound) + padding * 2);
      const treeHeight = Math.ceil((maxXBound - minXBound) + padding * 2);
      
      // Create high-resolution canvas
      const canvas = document.createElement('canvas');
      canvas.width = treeWidth * exportScale;
      canvas.height = treeHeight * exportScale;
      const ctx = canvas.getContext('2d');
      
      // Clear canvas (transparent background)
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Create temporary SVG for rendering
      const tempSvg = d3.create('svg')
        .attr('width', treeWidth * exportScale)
        .attr('height', treeHeight * exportScale)
        .attr('viewBox', `0 0 ${{treeWidth}} ${{treeHeight}}`);
      
      // Clone the tree structure
      const tempG = tempSvg.append('g')
        .attr('transform', `translate(${{ -minYBound + padding }}, ${{ -minXBound + padding }})`);
      
      // Use the already calculated export tree
      const tempLinks = exportRoot.links();
      tempG.selectAll('path')
        .data(tempLinks)
        .enter().append('path')
        .attr('d', diagonal)
        .attr('fill', 'none')
        .attr('stroke', lineColor)
        .attr('stroke-width', lineWidth)
        .attr('stroke-opacity', lineOpacity);
      
      // Render nodes
      const tempNodes = exportRoot.descendants();
      const nodeGroups = tempG.selectAll('g')
        .data(tempNodes)
        .enter().append('g')
        .attr('transform', d => `translate(${{d.y}}, ${{d.x}})`);
      
      // Use custom node shapes for export
      nodeGroups.each(function(d) {{
        createNodeShape(d3.select(this), nodeSize);
      }});
      
      // Add text with clean styling and proper positioning
      nodeGroups.append('text')
        .attr('dy', '-0.5em')  // Position text above the node
        .attr('x', 0)           // Center align horizontally
        .attr('text-anchor', 'middle')  // Center align the text
        .attr('font-family', 'Calibri, Arial, sans-serif')
        .attr('font-size', fontSize + 'px')
        .attr('font-weight', fontWeight)
        .attr('fill', '#111')
        .text(d => formatLabel(d));
      
      // Add region outlines for Mind Map exports
      if (styleMode === "Mind Map" && showGroupOutlines) {{
        const groups = exportRoot.descendants().filter(n => ((n.data && typeof n.data.level === 'number') ? n.data.level : n.depth) === groupOutlineLevel);
        const padX = nodeSize * 2.5;
        const padY = nodeSize * 2.0;
        const regions = groups.map(gNode => {{
          const desc = gNode.descendants();
          let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
          desc.forEach(d => {{
            if (d.x < minX) minX = d.x;
            if (d.x > maxX) maxX = d.x;
            if (d.y < minY) minY = d.y;
            if (d.y > maxY) maxY = d.y;
          }});
          const x = minY - padX;
          const y = minX - padY;
          const width = (maxY - minY) + padX * 2;
          const height = (maxX - minX) + padY * 2;
          return {{ key: gNode.id || (gNode.id = Math.random()), x, y, width, height, stroke: gNode.data.color || '#94A3B8' }};
        }});
        tempG.append('g')
          .selectAll('path')
          .data(regions, d => d.key)
          .enter().append('path')
          .attr('d', d => roundedRectPath(d.x, d.y, d.width, d.height, 18))
          .attr('fill', 'none')
          .attr('stroke', d => d.stroke)
          .attr('stroke-width', 2.5)
          .attr('stroke-dasharray', '8 6')
          .attr('opacity', outlineOpacity);
      }}

      // Convert SVG to data URL and download
      const svgData = new XMLSerializer().serializeToString(tempSvg.node());
      const svgBlob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
      const url = URL.createObjectURL(svgBlob);
      
      const img = new Image();
      img.onload = function() {{
        // Draw at native high-res size to avoid interpolation blur
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(function(blob) {{
          const link = document.createElement('a');
          link.download = `decomposition_tree_transparent_${{new Date().toISOString().slice(0,10)}}.png`;
          link.href = URL.createObjectURL(blob);
          link.click();
          URL.revokeObjectURL(url);
          URL.revokeObjectURL(link.href);
        }}, 'image/png', 1.0);
      }};
      img.src = url;
    }}
    
    function downloadPNGTransparent() {{
      // Create a complete tree with all nodes expanded for export
      const exportRoot = d3.hierarchy(data);
      exportRoot.descendants().forEach(d => {{
        if (d._children) d.children = d._children;
      }});
      
      // Calculate tree layout for export
      const exportTree = d3.tree().nodeSize([dx, dy]);
      exportTree(exportRoot);
      
      const nodes = exportRoot.descendants();
      if (nodes.length === 0) return;
      
      // Compute precise bounds including node shapes and labels
      const measure2 = document.createElement('canvas').getContext('2d');
      measure2.font = fontWeight + ' ' + fontSize + 'px Calibri, Arial, sans-serif';
      let minXBound2 = Infinity, maxXBound2 = -Infinity, minYBound2 = Infinity, maxYBound2 = -Infinity;
      nodes.forEach(d => {{
        const label = formatLabel(d);
        const textWidth = measure2.measureText(label).width;
        const halfText = textWidth / 2;
        const top = d.x - (nodeSize + fontSize + 8);
        const bottom = d.x + (nodeSize + 8);
        const left = d.y - Math.max(halfText, nodeSize);
        const right = d.y + Math.max(halfText, nodeSize);
        if (top < minXBound2) minXBound2 = top;
        if (bottom > maxXBound2) maxXBound2 = bottom;
        if (left < minYBound2) minYBound2 = left;
        if (right > maxYBound2) maxYBound2 = right;
      }});
      const basePadding2 = 40;
      const outlineExtraPadding2 = (styleMode === "Mind Map" && showGroupOutlines) ? Math.ceil(nodeSize * 3) : 0;
      const padding2 = basePadding2 + outlineExtraPadding2;
      const treeWidth = Math.ceil((maxYBound2 - minYBound2) + padding2 * 2);
      const treeHeight = Math.ceil((maxXBound2 - minXBound2) + padding2 * 2);
      
      // Create high-resolution canvas with white background
      const canvas = document.createElement('canvas');
      canvas.width = treeWidth * exportScale;
      canvas.height = treeHeight * exportScale;
      const ctx = canvas.getContext('2d');
      
      // Set white background
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      // Create temporary SVG for rendering
      const tempSvg = d3.create('svg')
        .attr('width', treeWidth * exportScale)
        .attr('height', treeHeight * exportScale)
        .attr('viewBox', `0 0 ${{treeWidth}} ${{treeHeight}}`)
        .style('background', '#ffffff');
      
      // Clone the tree structure
      const tempG = tempSvg.append('g')
        .attr('transform', `translate(${{ -minYBound2 + padding2 }}, ${{ -minXBound2 + padding2 }})`);
      
      // Use the already calculated export tree
      const tempLinks = exportRoot.links();
      tempG.selectAll('path')
        .data(tempLinks)
        .enter().append('path')
        .attr('d', diagonal)
        .attr('fill', 'none')
        .attr('stroke', lineColor)
        .attr('stroke-width', lineWidth)
        .attr('stroke-opacity', lineOpacity);
      
      // Render nodes
      const tempNodes = exportRoot.descendants();
      const nodeGroups = tempG.selectAll('g')
        .data(tempNodes)
        .enter().append('g')
        .attr('transform', d => `translate(${{d.y}}, ${{d.x}})`);
      
      // Use custom node shapes for export
      nodeGroups.each(function(d) {{
        createNodeShape(d3.select(this), nodeSize);
      }});
      
      // Add text with clean styling and proper positioning
      nodeGroups.append('text')
        .attr('dy', '-0.5em')  // Position text above the node
        .attr('x', 0)           // Center align horizontally
        .attr('text-anchor', 'middle')  // Center align the text
        .attr('font-family', 'Calibri, Arial, sans-serif')
        .attr('font-size', fontSize + 'px')
        .attr('font-weight', fontWeight)
        .attr('fill', '#111')
        .text(d => formatLabel(d));
      
      // Add region outlines for Mind Map exports
      if (styleMode === "Mind Map" && showGroupOutlines) {{
        const groups = exportRoot.descendants().filter(n => ((n.data && typeof n.data.level === 'number') ? n.data.level : n.depth) === groupOutlineLevel);
        const padX = nodeSize * 2.5;
        const padY = nodeSize * 2.0;
        const regions = groups.map(gNode => {{
          const desc = gNode.descendants();
          let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
          desc.forEach(d => {{
            if (d.x < minX) minX = d.x;
            if (d.x > maxX) maxX = d.x;
            if (d.y < minY) minY = d.y;
            if (d.y > maxY) maxY = d.y;
          }});
          const x = minY - padX;
          const y = minX - padY;
          const width = (maxY - minY) + padX * 2;
          const height = (maxX - minX) + padY * 2;
          return {{ key: gNode.id || (gNode.id = Math.random()), x, y, width, height, stroke: gNode.data.color || '#94A3B8' }};
        }});
        tempG.append('g')
          .selectAll('path')
          .data(regions, d => d.key)
          .enter().append('path')
          .attr('d', d => roundedRectPath(d.x, d.y, d.width, d.height, 18))
          .attr('fill', 'none')
          .attr('stroke', d => d.stroke)
          .attr('stroke-width', 2.5)
          .attr('stroke-dasharray', '8 6')
          .attr('opacity', outlineOpacity);
      }}

      // Convert SVG to data URL and download
      const svgData = new XMLSerializer().serializeToString(tempSvg.node());
      const svgBlob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
      const url = URL.createObjectURL(svgBlob);
      
      const img = new Image();
      img.onload = function() {{
        // Draw at native high-res size to avoid interpolation blur
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(function(blob) {{
          const link = document.createElement('a');
          link.download = `decomposition_tree_white_bg_${{new Date().toISOString().slice(0,10)}}.png`;
          link.href = URL.createObjectURL(blob);
          link.click();
          URL.revokeObjectURL(url);
          URL.revokeObjectURL(link.href);
        }}, 'image/png', 1.0);
      }};
      img.src = url;
    }}
    
    function downloadSVG() {{
      // Create a complete tree with all nodes expanded for export
      const exportRoot = d3.hierarchy(data);
      exportRoot.descendants().forEach(d => {{
        if (d._children) d.children = d._children;
      }});
      
      // Calculate tree layout for export
      const exportTree = d3.tree().nodeSize([dx, dy]);
      exportTree(exportRoot);
      
      const nodes = exportRoot.descendants();
      if (nodes.length === 0) return;
      
      // Compute precise bounds including node shapes and labels
      const measure3 = document.createElement('canvas').getContext('2d');
      measure3.font = fontWeight + ' ' + fontSize + 'px Calibri, Arial, sans-serif';
      let minXBound3 = Infinity, maxXBound3 = -Infinity, minYBound3 = Infinity, maxYBound3 = -Infinity;
      nodes.forEach(d => {{
        const label = formatLabel(d);
        const textWidth = measure3.measureText(label).width;
        const halfText = textWidth / 2;
        const top = d.x - (nodeSize + fontSize + 8);
        const bottom = d.x + (nodeSize + 8);
        const left = d.y - Math.max(halfText, nodeSize);
        const right = d.y + Math.max(halfText, nodeSize);
        if (top < minXBound3) minXBound3 = top;
        if (bottom > maxXBound3) maxXBound3 = bottom;
        if (left < minYBound3) minYBound3 = left;
        if (right > maxYBound3) maxYBound3 = right;
      }});
      const basePadding3 = 40;
      const outlineExtraPadding3 = (styleMode === "Mind Map" && showGroupOutlines) ? Math.ceil(nodeSize * 3) : 0;
      const padding3 = basePadding3 + outlineExtraPadding3;
      const treeWidth = Math.ceil((maxYBound3 - minYBound3) + padding3 * 2);
      const treeHeight = Math.ceil((maxXBound3 - minXBound3) + padding3 * 2);
      
      // Create SVG with transparent background
      const svg = d3.create('svg')
        .attr('width', treeWidth)
        .attr('height', treeHeight)
        .attr('xmlns', 'http://www.w3.org/2000/svg');
      
      // Clone the tree structure
      const g = svg.append('g')
        .attr('transform', `translate(${{ -minYBound3 + padding3 }}, ${{ -minXBound3 + padding3 }})`);
      
      // Use the already calculated export tree
      const links = exportRoot.links();
      g.selectAll('path')
        .data(links)
        .enter().append('path')
        .attr('d', diagonal)
        .attr('fill', 'none')
        .attr('stroke', lineColor)
        .attr('stroke-width', lineWidth)
        .attr('stroke-opacity', lineOpacity);
      
      // Render nodes
      const tempNodes = exportRoot.descendants();
      const nodeGroups = g.selectAll('g')
        .data(tempNodes)
        .enter().append('g')
        .attr('transform', d => `translate(${{d.y}}, ${{d.x}})`);
      
      // Use custom node shapes for export
      nodeGroups.each(function(d) {{
        createNodeShape(d3.select(this), nodeSize);
      }});
      
      // Add text with clean styling and proper positioning
      nodeGroups.append('text')
        .attr('dy', '-0.5em')  // Position text above the node
        .attr('x', 0)           // Center align horizontally
        .attr('text-anchor', 'middle')  // Center align the text
        .attr('font-family', 'Calibri, Arial, sans-serif')
        .attr('font-size', fontSize + 'px')
        .attr('font-weight', fontWeight)
        .attr('fill', '#111')
        .text(d => formatLabel(d));
      
      // Add region outlines for Mind Map exports
      if (styleMode === "Mind Map" && showGroupOutlines) {{
        const groups = exportRoot.descendants().filter(n => ((n.data && typeof n.data.level === 'number') ? n.data.level : n.depth) === groupOutlineLevel);
        const padX = nodeSize * 2.5;
        const padY = nodeSize * 2.0;
        const regions = groups.map(gNode => {{
          const desc = gNode.descendants();
          let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
          desc.forEach(d => {{
            if (d.x < minX) minX = d.x;
            if (d.x > maxX) maxX = d.x;
            if (d.y < minY) minY = d.y;
            if (d.y > maxY) maxY = d.y;
          }});
          const x = minY - padX;
          const y = minX - padY;
          const width = (maxY - minY) + padX * 2;
          const height = (maxX - minX) + padY * 2;
          return {{ key: gNode.id || (gNode.id = Math.random()), x, y, width, height, stroke: gNode.data.color || '#94A3B8' }};
        }});
        g.append('g')
          .selectAll('path')
          .data(regions, d => d.key)
          .enter().append('path')
          .attr('d', d => roundedRectPath(d.x, d.y, d.width, d.height, 18))
          .attr('fill', 'none')
          .attr('stroke', d => d.stroke)
          .attr('stroke-width', 2.5)
          .attr('stroke-dasharray', '8 6')
          .attr('opacity', outlineOpacity);
      }}

      // Download SVG
      const svgData = new XMLSerializer().serializeToString(svg.node());
      const blob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.download = `decomposition_tree_${{new Date().toISOString().slice(0,10)}}.svg`;
      link.href = url;
      link.click();
      URL.revokeObjectURL(url);
    }}
    
    function downloadSVGTransparent() {{
      // Create a complete tree with all nodes expanded for export
      const exportRoot = d3.hierarchy(data);
      exportRoot.descendants().forEach(d => {{
        if (d._children) d.children = d._children;
      }});
      
      // Calculate tree layout for export
      const exportTree = d3.tree().nodeSize([dx, dy]);
      exportTree(exportRoot);
      
      const nodes = exportRoot.descendants();
      if (nodes.length === 0) return;
      
      // Compute precise bounds including node shapes and labels
      const measure4 = document.createElement('canvas').getContext('2d');
      measure4.font = fontWeight + ' ' + fontSize + 'px Calibri, Arial, sans-serif';
      let minXBound4 = Infinity, maxXBound4 = -Infinity, minYBound4 = Infinity, maxYBound4 = -Infinity;
      nodes.forEach(d => {{
        const label = formatLabel(d);
        const textWidth = measure4.measureText(label).width;
        const halfText = textWidth / 2;
        const top = d.x - (nodeSize + fontSize + 8);
        const bottom = d.x + (nodeSize + 8);
        const left = d.y - Math.max(halfText, nodeSize);
        const right = d.y + Math.max(halfText, nodeSize);
        if (top < minXBound4) minXBound4 = top;
        if (bottom > maxXBound4) maxXBound4 = bottom;
        if (left < minYBound4) minYBound4 = left;
        if (right > maxYBound4) maxYBound4 = right;
      }});
      const basePadding4 = 40;
      const outlineExtraPadding4 = (styleMode === "Mind Map" && showGroupOutlines) ? Math.ceil(nodeSize * 3) : 0;
      const padding4 = basePadding4 + outlineExtraPadding4;
      const treeWidth = Math.ceil((maxYBound4 - minYBound4) + padding4 * 2);
      const treeHeight = Math.ceil((maxXBound4 - minXBound4) + padding4 * 2);
      
      // Create SVG with white background
      const svg = d3.create('svg')
        .attr('width', treeWidth)
        .attr('height', treeHeight)
        .attr('xmlns', 'http://www.w3.org/2000/svg')
        .style('background', '#ffffff');
      
      // Add white background rectangle
      svg.append('rect')
        .attr('width', '100%')
        .attr('height', '100%')
        .attr('fill', '#ffffff');
      
      // Clone the tree structure
      const g = svg.append('g')
        .attr('transform', `translate(${{ -minYBound4 + padding4 }}, ${{ -minXBound4 + padding4 }})`);
      
      // Use the already calculated export tree
      const links = exportRoot.links();
      g.selectAll('path')
        .data(links)
        .enter().append('path')
        .attr('d', diagonal)
        .attr('fill', 'none')
        .attr('stroke', lineColor)
        .attr('stroke-width', lineWidth)
        .attr('stroke-opacity', lineOpacity);
      
      // Render nodes
      const tempNodes = exportRoot.descendants();
      const nodeGroups = g.selectAll('g')
        .data(tempNodes)
        .enter().append('g')
        .attr('transform', d => `translate(${{d.y}}, ${{d.x}})`);
      
      // Use custom node shapes for export
      nodeGroups.each(function(d) {{
        createNodeShape(d3.select(this), nodeSize);
      }});
      
      // Add text with clean styling and proper positioning
      nodeGroups.append('text')
        .attr('dy', '-0.5em')  // Position text above the node
        .attr('x', 0)           // Center align horizontally
        .attr('text-anchor', 'middle')  // Center align the text
        .attr('font-family', 'Calibri, Arial, sans-serif')
        .attr('font-size', fontSize + 'px')
        .attr('font-weight', fontWeight)
        .attr('fill', '#111')
        .text(d => formatLabel(d));
      
      // Add region outlines for Mind Map exports
      if (styleMode === "Mind Map" && showGroupOutlines) {{
        const groups = exportRoot.descendants().filter(n => ((n.data && typeof n.data.level === 'number') ? n.data.level : n.depth) === groupOutlineLevel);
        const padX = nodeSize * 2.5;
        const padY = nodeSize * 2.0;
        const regions = groups.map(gNode => {{
          const desc = gNode.descendants();
          let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
          desc.forEach(d => {{
            if (d.x < minX) minX = d.x;
            if (d.x > maxX) maxX = d.x;
            if (d.y < minY) minY = d.y;
            if (d.y > maxY) maxY = d.y;
          }});
          const x = minY - padX;
          const y = minX - padY;
          const width = (maxY - minY) + padX * 2;
          const height = (maxX - minX) + padY * 2;
          return {{ key: gNode.id || (gNode.id = Math.random()), x, y, width, height, stroke: gNode.data.color || '#94A3B8' }};
        }});
        g.append('g')
          .selectAll('path')
          .data(regions, d => d.key)
          .enter().append('path')
          .attr('d', d => roundedRectPath(d.x, d.y, d.width, d.height, 18))
          .attr('fill', 'none')
          .attr('stroke', d => d.stroke)
          .attr('stroke-width', 2.5)
          .attr('stroke-dasharray', '8 6')
          .attr('opacity', outlineOpacity);
      }}

      // Download SVG
      const svgData = new XMLSerializer().serializeToString(svg.node());
      const blob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.download = `decomposition_tree_white_bg_${{new Date().toISOString().slice(0,10)}}.svg`;
      link.href = url;
      link.click();
      URL.revokeObjectURL(url);
    }}
    
    // New functions for current view export
    function downloadCurrentViewPNG() {{
      // Use the current tree state (with collapsed/expanded nodes as they are)
      const currentRoot = root.copy();
      
      // Calculate tree layout for current view
      const currentTree = d3.tree().nodeSize([dx, dy]);
      currentTree(currentRoot);
      
      const nodes = currentRoot.descendants();
      if (nodes.length === 0) return;
      
      // Compute precise bounds including node shapes and labels
      const measure5 = document.createElement('canvas').getContext('2d');
      measure5.font = fontWeight + ' ' + fontSize + 'px Calibri, Arial, sans-serif';
      let minXBound5 = Infinity, maxXBound5 = -Infinity, minYBound5 = Infinity, maxYBound5 = -Infinity;
      nodes.forEach(d => {{
        const label = formatLabel(d);
        const textWidth = measure5.measureText(label).width;
        const halfText = textWidth / 2;
        const top = d.x - (nodeSize + fontSize + 8);
        const bottom = d.x + (nodeSize + 8);
        const left = d.y - Math.max(halfText, nodeSize);
        const right = d.y + Math.max(halfText, nodeSize);
        if (top < minXBound5) minXBound5 = top;
        if (bottom > maxXBound5) maxXBound5 = bottom;
        if (left < minYBound5) minYBound5 = left;
        if (right > maxYBound5) maxYBound5 = right;
      }});
      const basePadding5 = 40;
      const outlineExtraPadding5 = (styleMode === "Mind Map" && showGroupOutlines) ? Math.ceil(nodeSize * 3) : 0;
      const padding5 = basePadding5 + outlineExtraPadding5;
      const treeWidth = Math.ceil((maxYBound5 - minYBound5) + padding5 * 2);
      const treeHeight = Math.ceil((maxXBound5 - minXBound5) + padding5 * 2);
      
      // Create high-resolution canvas
      const canvas = document.createElement('canvas');
      canvas.width = treeWidth * exportScale;
      canvas.height = treeHeight * exportScale;
      const ctx = canvas.getContext('2d');
      
      // Clear canvas (transparent background)
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Create temporary SVG for rendering
      const tempSvg = d3.create('svg')
        .attr('width', treeWidth * exportScale)
        .attr('height', treeHeight * exportScale)
        .attr('viewBox', `0 0 ${{treeWidth}} ${{treeHeight}}`);
      
      // Clone the tree structure
      const tempG = tempSvg.append('g')
        .attr('transform', `translate(${{ -minYBound5 + padding5 }}, ${{ -minXBound5 + padding5 }})`);
      
      // Use the current tree links
      const currentLinks = currentRoot.links();
      tempG.selectAll('path')
        .data(currentLinks)
        .enter().append('path')
        .attr('d', diagonal)
        .attr('fill', 'none')
        .attr('stroke', lineColor)
        .attr('stroke-width', lineWidth)
        .attr('stroke-opacity', lineOpacity);
      
      // Render nodes
      const nodeGroups = tempG.selectAll('g')
        .data(nodes)
        .enter().append('g')
        .attr('transform', d => `translate(${{d.y}}, ${{d.x}})`);
      
      // Use custom node shapes for export
      nodeGroups.each(function(d) {{
        createNodeShape(d3.select(this), nodeSize);
      }});
      
      // Add text with clean styling and proper positioning
      nodeGroups.append('text')
        .attr('dy', '-0.5em')  // Position text above the node
        .attr('x', 0)           // Center align horizontally
        .attr('text-anchor', 'middle')  // Center align the text
        .attr('font-family', 'Calibri, Arial, sans-serif')
        .attr('font-size', fontSize + 'px')
        .attr('font-weight', fontWeight)
        .attr('fill', '#111')
        .text(d => formatLabel(d));
      
      // Add region outlines for Mind Map exports
      if (styleMode === "Mind Map" && showGroupOutlines) {{
        const groups = currentRoot.descendants().filter(n => ((n.data && typeof n.data.level === 'number') ? n.data.level : n.depth) === groupOutlineLevel);
        const padX = nodeSize * 2.5;
        const padY = nodeSize * 2.0;
        const regions = groups.map(gNode => {{
          const desc = gNode.descendants();
          let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
          desc.forEach(d => {{
            if (d.x < minX) minX = d.x;
            if (d.x > maxX) maxX = d.x;
            if (d.y < minY) minY = d.y;
            if (d.y > maxY) maxY = d.y;
          }});
          const x = minY - padX;
          const y = minX - padY;
          const width = (maxY - minY) + padX * 2;
          const height = (maxX - minX) + padY * 2;
          return {{ key: gNode.id || (gNode.id = Math.random()), x, y, width, height, stroke: gNode.data.color || '#94A3B8' }};
        }});
        tempG.append('g')
          .selectAll('path')
          .data(regions, d => d.key)
          .enter().append('path')
          .attr('d', d => roundedRectPath(d.x, d.y, d.width, d.height, 18))
          .attr('fill', 'none')
          .attr('stroke', d => d.stroke)
          .attr('stroke-width', 2.5)
          .attr('stroke-dasharray', '8 6')
          .attr('opacity', outlineOpacity);
      }}

      // Convert SVG to data URL and download
      const svgData = new XMLSerializer().serializeToString(tempSvg.node());
      const svgBlob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
      const url = URL.createObjectURL(svgBlob);
      
      const img = new Image();
      img.onload = function() {{
        // Draw at native high-res size to avoid interpolation blur
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(function(blob) {{
          const link = document.createElement('a');
          link.download = `decomposition_tree_current_view_${{new Date().toISOString().slice(0,10)}}.png`;
          link.href = URL.createObjectURL(blob);
          link.click();
          URL.revokeObjectURL(url);
          URL.revokeObjectURL(link.href);
        }}, 'image/png', 1.0);
      }};
      img.src = url;
    }}
    
    function downloadCurrentViewSVG() {{
      // Use the current tree state (with collapsed/expanded nodes as they are)
      const currentRoot = root.copy();
      
      // Calculate tree layout for current view
      const currentTree = d3.tree().nodeSize([dx, dy]);
      currentTree(currentRoot);
      
      const nodes = currentRoot.descendants();
      if (nodes.length === 0) return;
      
      // Compute precise bounds including node shapes and labels
      const measure6 = document.createElement('canvas').getContext('2d');
      measure6.font = fontWeight + ' ' + fontSize + 'px Calibri, Arial, sans-serif';
      let minXBound6 = Infinity, maxXBound6 = -Infinity, minYBound6 = Infinity, maxYBound6 = -Infinity;
      nodes.forEach(d => {{
        const label = formatLabel(d);
        const textWidth = measure6.measureText(label).width;
        const halfText = textWidth / 2;
        const top = d.x - (nodeSize + fontSize + 8);
        const bottom = d.x + (nodeSize + 8);
        const left = d.y - Math.max(halfText, nodeSize);
        const right = d.y + Math.max(halfText, nodeSize);
        if (top < minXBound6) minXBound6 = top;
        if (bottom > maxXBound6) maxXBound6 = bottom;
        if (left < minYBound6) minYBound6 = left;
        if (right > maxYBound6) maxYBound6 = right;
      }});
      const basePadding6 = 40;
      const outlineExtraPadding6 = (styleMode === "Mind Map" && showGroupOutlines) ? Math.ceil(nodeSize * 3) : 0;
      const padding6 = basePadding6 + outlineExtraPadding6;
      const treeWidth = Math.ceil((maxYBound6 - minYBound6) + padding6 * 2);
      const treeHeight = Math.ceil((maxXBound6 - minXBound6) + padding6 * 2);
      
      // Create SVG with transparent background
      const svg = d3.create('svg')
        .attr('width', treeWidth)
        .attr('height', treeHeight)
        .attr('xmlns', 'http://www.w3.org/2000/svg');
      
      // Clone the tree structure
      const g = svg.append('g')
        .attr('transform', `translate(${{ -minYBound6 + padding6 }}, ${{ -minXBound6 + padding6 }})`);
      
      // Use the current tree links
      const links = currentRoot.links();
      g.selectAll('path')
        .data(links)
        .enter().append('path')
        .attr('d', diagonal)
        .attr('fill', 'none')
        .attr('stroke', lineColor)
        .attr('stroke-width', lineWidth)
        .attr('stroke-opacity', lineOpacity);
      
      // Render nodes
      const nodeGroups = g.selectAll('g')
        .data(nodes)
        .enter().append('g')
        .attr('transform', d => `translate(${{d.y}}, ${{d.x}})`);
      
      // Use custom node shapes for export
      nodeGroups.each(function(d) {{
        createNodeShape(d3.select(this), nodeSize);
      }});
      
      // Add text with clean styling and proper positioning
      nodeGroups.append('text')
        .attr('dy', '-0.5em')
        .attr('x', 0)
        .attr('text-anchor', 'middle')
        .attr('font-family', 'Calibri, Arial, sans-serif')
        .attr('font-size', fontSize + 'px')
        .attr('font-weight', fontWeight)
        .attr('fill', '#111')
        .text(d => formatLabel(d));
      
      // Add region outlines for Mind Map exports
      if (styleMode === "Mind Map" && showGroupOutlines) {{
        const groups = currentRoot.descendants().filter(n => ((n.data && typeof n.data.level === 'number') ? n.data.level : n.depth) === groupOutlineLevel);
        const padX = nodeSize * 2.5;
        const padY = nodeSize * 2.0;
        const regions = groups.map(gNode => {{
          const desc = gNode.descendants();
          let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
          desc.forEach(d => {{
            if (d.x < minX) minX = d.x;
            if (d.x > maxX) maxX = d.x;
            if (d.y < minY) minY = d.y;
            if (d.y > maxY) maxY = d.y;
          }});
          const x = minY - padX;
          const y = minX - padY;
          const width = (maxY - minY) + padX * 2;
          const height = (maxX - minX) + padY * 2;
          return {{ key: gNode.id || (gNode.id = Math.random()), x, y, width, height, stroke: gNode.data.color || '#94A3B8' }};
        }});
        g.append('g')
          .selectAll('path')
          .data(regions, d => d.key)
          .enter().append('path')
          .attr('d', d => roundedRectPath(d.x, d.y, d.width, d.height, 18))
          .attr('fill', 'none')
          .attr('stroke', d => d.stroke)
          .attr('stroke-width', 2.5)
          .attr('stroke-dasharray', '8 6')
          .attr('opacity', outlineOpacity);
      }}

      // Download SVG
      const svgData = new XMLSerializer().serializeToString(svg.node());
      const blob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.download = `decomposition_tree_current_view_${{new Date().toISOString().slice(0,10)}}.svg`;
      link.href = url;
      link.click();
      URL.revokeObjectURL(url);
    }}
    
    // Context menu functions
    function showContextMenu(event, node) {{
      event.preventDefault();
      selectedNode = node;
      
      if (!contextMenu) {{
        contextMenu = document.getElementById('contextMenu');
        nodeDataPanel = document.getElementById('nodeDataPanel');
      }}
      
      contextMenu.style.display = 'block';
      contextMenu.style.left = event.pageX + 'px';
      contextMenu.style.top = event.pageY + 'px';
    }}
    
    function hideContextMenu() {{
      if (contextMenu) {{
        contextMenu.style.display = 'none';
      }}
      if (nodeDataPanel) {{
        nodeDataPanel.style.display = 'none';
      }}
    }}
    
    function downloadNodeData() {{
      if (!selectedNode) return;
      
      // Get all data for this node and its descendants
      const nodeData = getNodeData(selectedNode);
      
      // Convert to CSV
      const csvContent = convertToCSV(nodeData);
      
      // Download CSV
      const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `node_data_${{selectedNode.data.name.replace(/[^a-zA-Z0-9]/g, '_')}}_${{new Date().toISOString().slice(0,10)}}.csv`;
      link.click();
      URL.revokeObjectURL(link.href);
      
      hideContextMenu();
    }}
    
    function downloadNodeDataExcel() {{
      if (!selectedNode) return;
      
      // Get all data for this node and its descendants
      const nodeData = getNodeData(selectedNode);
      
      // Convert to Excel format (CSV with BOM for Excel compatibility)
      const csvContent = '\ufeff' + convertToCSV(nodeData);
      
      // Download Excel
      const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `node_data_${{selectedNode.data.name.replace(/[^a-zA-Z0-9]/g, '_')}}_${{new Date().toISOString().slice(0,10)}}.xlsx`;
      link.click();
      URL.revokeObjectURL(link.href);
      
      hideContextMenu();
    }}
    
    function showNodeDetails() {{
      if (!selectedNode || !nodeDataPanel) return;
      
      const nodeData = getNodeData(selectedNode);
      const content = document.getElementById('nodeDataContent');
      
      let html = `<div class="data-item"><span class="data-label">Node:</span> <span class="data-value">${{selectedNode.data.name}}</span></div>`;
      html += `<div class="data-item"><span class="data-label">Value:</span> <span class="data-value">${{selectedNode.data.value || 0}}</span></div>`;
      html += `<div class="data-item"><span class="data-label">Records:</span> <span class="data-value">${{nodeData.length}}</span></div>`;
      
      // Show tooltip data
      if (selectedNode.data.tooltip_data) {{
        for (const [key, value] of Object.entries(selectedNode.data.tooltip_data)) {{
          html += `<div class="data-item"><span class="data-label">${{key}}:</span> <span class="data-value">${{value}}</span></div>`;
        }}
      }}
      
      content.innerHTML = html;
      nodeDataPanel.style.display = 'block';
      
      // Auto-hide after 5 seconds
      setTimeout(() => {{
        nodeDataPanel.style.display = 'none';
      }}, 5000);
      
      hideContextMenu();
    }}
    
    function downloadNodeTree() {{
      if (!selectedNode) return;
      
      // Get the subtree structure
      const subtree = getNodeSubtree(selectedNode);
      
      // Download JSON
      const jsonContent = JSON.stringify(subtree, null, 2);
      const blob = new Blob([jsonContent], {{ type: 'application/json;charset=utf-8;' }});
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `node_tree_${{selectedNode.data.name.replace(/[^a-zA-Z0-9]/g, '_')}}_${{new Date().toISOString().slice(0,10)}}.json`;
      link.click();
      URL.revokeObjectURL(link.href);
      
      hideContextMenu();
    }}
    
    function getNodeData(node) {{
      // This function would need to be implemented based on your data structure
      // For now, we'll return a placeholder that shows the node's aggregated data
      const data = [];
      
      // Add the node's own data
      if (node.data.raw_data) {{
        data.push(...node.data.raw_data);
      }}
      
      // Add data from all descendants
      node.descendants().forEach(descendant => {{
        if (descendant !== node && descendant.data.raw_data) {{
          data.push(...descendant.data.raw_data);
        }}
      }});
      
      return data;
    }}
    
    function getNodeSubtree(node) {{
      // Create a clean subtree structure for JSON export
      const subtree = {{
        name: node.data.name,
        value: node.data.value,
        level: node.data.level,
        column: node.data.column,
        node_value: node.data.node_value,
        color: node.data.color,
        tooltip_data: node.data.tooltip_data,
        children: []
      }};
      
      if (node.children) {{
        node.children.forEach(child => {{
          subtree.children.push(getNodeSubtree(child));
        }});
      }}
      
      return subtree;
    }}
    
    function convertToCSV(data) {{
      if (!data || data.length === 0) {{
        return "No data available for this node";
      }}
      
      // Get all unique keys from the data
      const keys = new Set();
      data.forEach(item => {{
        Object.keys(item).forEach(key => keys.add(key));
      }});
      
      const headers = Array.from(keys);
      const csvRows = [headers.join(',')];
      
      data.forEach(item => {{
        const row = headers.map(header => {{
          const value = item[header] || '';
          // Escape commas and quotes in CSV
          if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {{
            return `"${{value.replace(/"/g, '""')}}"`;
          }}
          return value;
        }});
        csvRows.push(row.join(','));
      }});
      
      return csvRows.join('\\n');
    }}
    
    // Hide context menu when clicking elsewhere
    document.addEventListener('click', hideContextMenu);
    
    function update(source) {{
      tree(root);
      const nodes = root.descendants();
      const links = root.links();
      
      // Update links (color per-branch in Mind Map mode)
      const link = gLink.selectAll("path").data(links, d => d.target.id || (d.target.id = Math.random()));
      link.enter().append("path")
        .attr("class", "link")
        .attr("d", diagonal)
        .attr("fill", "none")
        .attr("stroke-width", lineWidth)
        .attr("stroke-linecap", "round")
        .attr("stroke-linejoin", "round")
        .attr("stroke", d => styleMode === "Mind Map" ? (d.target.data.color || lineColor) : lineColor)
        .merge(link)
        .transition().duration(750)
        .attr("d", diagonal)
        .attr("stroke-width", lineWidth)
        .attr("stroke-linecap", "round")
        .attr("stroke-linejoin", "round")
        .attr("stroke", d => styleMode === "Mind Map" ? (d.target.data.color || lineColor) : lineColor);
      link.exit().remove();

      // Region outlines for Mind Map style
      if (styleMode === "Mind Map" && showGroupOutlines) {{
        const groups = nodes.filter(n => (n.data && typeof n.data.level === 'number' ? n.data.level : n.depth) === groupOutlineLevel);
        const padX = nodeSize * 2.5;
        const padY = nodeSize * 2.0;
        const regions = groups.map(g => {{
          const desc = g.descendants();
          let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
          desc.forEach(d => {{
            if (d.x < minX) minX = d.x;
            if (d.x > maxX) maxX = d.x;
            if (d.y < minY) minY = d.y;
            if (d.y > maxY) maxY = d.y;
          }});
          const x = minY - padX;
          const y = minX - padY;
          const width = (maxY - minY) + padX * 2;
          const height = (maxX - minX) + padY * 2;
          return {{ key: g.id || (g.id = Math.random()), x, y, width, height, stroke: g.data.color || '#94A3B8' }};
        }});
        const regionSel = gRegion.selectAll('path').data(regions, d => d.key);
        regionSel.enter().append('path')
          .attr('class', 'region-outline')
          .attr('opacity', outlineOpacity)
          .attr('d', d => roundedRectPath(d.x, d.y, d.width, d.height, 18))
          .attr('stroke', d => d.stroke)
          .merge(regionSel)
          .transition().duration(600)
          .attr('d', d => roundedRectPath(d.x, d.y, d.width, d.height, 18))
          .attr('stroke', d => d.stroke)
          .attr('opacity', outlineOpacity);
        regionSel.exit().remove();
      }} else {{
        gRegion.selectAll('*').remove();
      }}
      
      // Update nodes
      const node = gNode.selectAll("g").data(nodes, d => d.id || (d.id = Math.random()));
      
      // Enter new nodes
      const nodeEnter = node.enter().append("g")
        .attr("class", "node")
        .attr("transform", d => `translate(${{source.y0 || 0}},${{source.x0 || 0}})`)
        .on("click", (event, d) => {{
          // Ignore click if a drag just occurred
          if (dragActive || event.defaultPrevented) return;
          if (d._children) {{
            d.children = d.children ? null : d._children;
          }}
          update(d);
        }})
        .on("contextmenu", (event, d) => {{
          showContextMenu(event, d);
        }})
        .on("mouseover", (event, d) => {{
          let t = `<b>${{d.data.name}}</b><br>`;
          for (const [k,v] of Object.entries(d.data.tooltip_data||{{}}))
            t += `${{k}}: <span style='color:#38bdf8;font-weight:600'>${{v}}</span><br>`;
          tooltip.transition().duration(200).style("opacity", .95);
          tooltip.html(t).style("left", (event.pageX+15) + "px").style("top", (event.pageY-20) + "px");
        }})
        .on("mouseout", () => tooltip.transition().duration(400).style("opacity", 0));
      
      // Add shapes to new nodes using the custom shape function
      nodeEnter.each(function(d) {{
        createNodeShape(d3.select(this), nodeSize);
      }});
      
      // Add text to new nodes with clean styling and proper positioning
      nodeEnter.append("text")
        .attr("dy", "-0.5em")  // Position text above the node
        .attr("x", 0)           // Center align horizontally
        .attr("text-anchor", "middle")  // Center align the text
        .attr("font-family", "Calibri, Arial, sans-serif")
        .attr("font-size", fontSize + "px")
        .attr("font-weight", fontWeight)
        .attr("fill", "#111")
        .attr("pointer-events", "none")  // Prevent text from interfering with node clicks
        .text(d => formatLabel(d));
      
      // Drag & drop reorder among siblings
      const dragBehavior = d3.drag()
        .on("start", function(event, d) {{
          if (!enableDragReorder) return;
          // Prevent zoom/pan from interfering while dragging
          if (event.sourceEvent) {{ event.sourceEvent.stopPropagation(); }}
          dragActive = true;
          d3.select(this).raise().classed("dragging", true);
        }})
        .on("drag", function(event, d) {{
          if (!enableDragReorder) return;
          const [, py] = d3.pointer(event, g.node());
          d3.select(this).attr("transform", `translate(${{d.y}}, ${{py}})`);
        }})
        .on("end", function(event, d) {{
          if (!enableDragReorder) return;
          // Mark the preceding click as prevented so it won't toggle
          event.sourceEvent && (event.sourceEvent.preventDefault(), event.sourceEvent.stopPropagation());
          dragActive = false;
          d3.select(this).classed("dragging", false);
          const parent = d.parent;
          if (!parent) return;
          manualOrder = true;
          const container = parent.children ? parent.children : parent._children;
          if (!container) return;
          const siblings = container.filter(s => s !== d).sort((a, b) => a.x - b.x);
          const [, py] = d3.pointer(event, g.node());
          // Find index to insert based on vertical position relative to siblings
          let dropIndex = siblings.findIndex(s => py < s.x);
          if (dropIndex === -1) dropIndex = siblings.length;
          // Build a new ordered array: insert dragged node at dropIndex among sorted siblings
          const newOrder = [];
          for (let i = 0; i < siblings.length; i++) {{
            if (i === dropIndex) newOrder.push(d);
            newOrder.push(siblings[i]);
          }}
          if (dropIndex === siblings.length) newOrder.push(d);
          if (parent.children) {{ parent.children = newOrder; }} else {{ parent._children = newOrder; }}
          update(parent);
        }});

      if (enableDragReorder) {{
        nodeEnter.call(dragBehavior);
      }}

      // Update existing nodes
      const nodeUpdate = node.merge(nodeEnter)
        .attr("pointer-events", "all");

      nodeUpdate
        .transition().duration(700)
        .attr("transform", d => `translate(${{d.y}},${{d.x}})`);
      
      if (enableDragReorder) {{
        nodeUpdate.call(dragBehavior);
      }}
      if (enableDragReorder) {{
        node.merge(nodeEnter).call(dragBehavior);
      }}
      
      // Remove old nodes
      node.exit().remove();
      
      // Store positions for next update
      root.each(d => {{ d.x0 = d.x; d.y0 = d.y; }});
    }}
    
    // Initial update
    update(root);
    
    // Center the tree initially
    setTimeout(() => {{
      const nodes = root.descendants();
      if (nodes.length > 0) {{
        const minX = d3.min(nodes, d => d.x);
        const maxX = d3.max(nodes, d => d.x);
        const minY = d3.min(nodes, d => d.y);
        const maxY = d3.max(nodes, d => d.y);
        const treeWidth = maxY - minY;
        const treeHeight = maxX - minX;
        const centerX = width / 2 - (minY + treeWidth / 2);
        const centerY = height / 2 - (minX + treeHeight / 2);
        svg.call(zoom.transform, d3.zoomIdentity.translate(centerX, centerY).scale(1));
      }}
    }}, 100);
    </script>
    </body>
    </html>
    """
    st.header("🎯 Interactive Decomposition Tree")
    st.info("💡 **Right-click on any node** to download data, view details, or export the subtree structure!")
    
    # Add export explanation
    with st.expander("📥 Export Options Explained"):
        st.markdown("""
        **Export Options:**
        
        🖼️ **Complete Tree Export** (PNG/SVG):
        - Shows ALL nodes expanded regardless of current view
        - Best for comprehensive reports and data sharing
        - Ensures no information is missed
        
        🖼️ **Current View Export** (PNG/SVG):
        - Shows only what you currently see (expanded/collapsed state)
        - Best for focused presentations and specific analysis
        - Respects your current tree navigation
        
        **Recommendation:** Use "Complete Tree" for official reports and "Current View" for focused presentations.
        """)
    
    # Status distribution and samples removed
    st.components.v1.html(d3_html, height=900)
    csv = df.to_csv(index=False)
    st.sidebar.download_button("📥 Download All Data CSV", csv, "all_sites.csv", "text/csv")
else:
    st.info("Please upload an Excel file to start analysis.")
