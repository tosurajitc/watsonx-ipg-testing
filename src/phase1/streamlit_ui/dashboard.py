"""
dashboard.py - Dashboard/Home Screen for Watsonx IPG Testing Platform

This module provides the dashboard view with overview widgets, summaries, and quick actions.
It serves as the main landing page for authenticated users.
"""
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import random  # For demo data - remove in production
from ui_utils import create_card, create_metric_card, create_chart
from components import notification_badge
import mock_services  # Import mock services for demo data

#################### Testing blocl


def show_dashboard():
    """Display the dashboard module."""
    st.header("Dashboard")
    
    # Get mock data
    pending_tasks = mock_services.get_pending_tasks()
    recent_activity = mock_services.get_recent_activity()
    defects = mock_services.get_defects()
    execution_runs = mock_services.get_execution_runs()
    
    # Calculate summary metrics
    total_test_cases = len(mock_services.get_test_cases())
    total_executions = len(execution_runs)
    pass_count = sum(run["pass_count"] for run in execution_runs)
    fail_count = sum(run["fail_count"] for run in execution_runs)
    total_defects = len(defects)
    
    # Layout
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        create_metric_card("Test Cases", total_test_cases)
    
    with col2:
        create_metric_card("Executions", total_executions)
    
    with col3:
        pass_rate = f"{int(pass_count/(pass_count + fail_count) * 100)}%" if pass_count + fail_count > 0 else "N/A"
        create_metric_card("Pass Rate", pass_rate)
    
    with col4:
        create_metric_card("Open Defects", total_defects)
    
    st.markdown("---")
    
    # Quick Actions section
    st.subheader("Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Generate Tests from Requirements"):
            st.session_state["page"] = "Requirements"
            st.experimental_rerun()
    
    with col2:
        if st.button("Review Existing Test Case"):
            st.session_state["page"] = "Test Repository"
            st.experimental_rerun()
    
    with col3:
        if st.button("Analyze Failed Test"):
            st.session_state["page"] = "Analysis & Defects"
            st.experimental_rerun()
    
    st.markdown("---")
    
    # Pending Tasks widget
    st.subheader("Pending Tasks")
    
    if pending_tasks:
        pending_df = pd.DataFrame(pending_tasks)
        st.dataframe(pending_df, use_container_width=True)
    else:
        st.info("No pending tasks.")
    
    # Recent Activity widget
    st.subheader("Recent Activity")
    
    if recent_activity:
        activity_df = pd.DataFrame(recent_activity)
        st.dataframe(activity_df, use_container_width=True)
    else:
        st.info("No recent activity.")
    
    # Test Execution Summary widget
    st.subheader("Test Execution Summary")
    
    if execution_runs:
        # Create chart data
        chart_data = []
        for run in execution_runs[:5]:  # Last 5 runs
            chart_data.append({
                "Run ID": run["id"],
                "Passed": run["pass_count"],
                "Failed": run["fail_count"],
                "Blocked": run["blocked_count"]
            })
        
        chart_df = pd.DataFrame(chart_data)
        
        # Create stacked bar chart
        st.bar_chart(chart_df.set_index("Run ID"))
    else:
        st.info("No execution data available.")
    
    # Defect Summary widget
    st.subheader("Defect Summary")
    
    if defects:
        # Count defects by status
        status_counts = {}
        for defect in defects:
            status = defect["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Create pie chart data
        pie_data = [{"Status": status, "Count": count} for status, count in status_counts.items()]
        pie_df = pd.DataFrame(pie_data)
        
        # Create pie chart
        fig = create_chart(pie_df, "pie", "Status", "Count", "Defects by Status")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No defect data available.")



################### Testing block endss here





# Mock data functions - replace with actual data sources in production
def get_pending_tasks():
    """Get list of pending tasks that need user attention"""
    tasks = [
        {"id": "TSK001", "type": "Review", "description": "Review suggested changes to Login Test Cases", "priority": "High", "due_date": "2025-04-28"},
        {"id": "TSK002", "type": "Approve", "description": "Approve new test cases for Payment Module", "priority": "Medium", "due_date": "2025-04-29"},
        {"id": "TSK003", "type": "Review", "description": "Review failed manual tests for User Profile", "priority": "High", "due_date": "2025-04-27"},
        {"id": "TSK004", "type": "Update", "description": "Update test data for Checkout flow", "priority": "Low", "due_date": "2025-05-01"},
        {"id": "TSK005", "type": "Validate", "description": "Validate UFT script generation for Admin Panel", "priority": "Medium", "due_date": "2025-04-30"}
    ]
    return pd.DataFrame(tasks)

def get_recent_activity():
    """Get list of recent system activities"""
    activities = [
        {"timestamp": "2025-04-26 09:15:22", "user": "john.doe", "action": "Generated 15 test cases for Payment Module"},
        {"timestamp": "2025-04-26 08:45:11", "user": "jane.smith", "action": "Executed Regression Suite #24"},
        {"timestamp": "2025-04-25 17:30:45", "user": "robert.johnson", "action": "Created Defect IPG-345: 'Payment Timeout Error'"},
        {"timestamp": "2025-04-25 15:20:33", "user": "sarah.wilson", "action": "Updated User Profile Test Cases"},
        {"timestamp": "2025-04-25 11:05:18", "user": "david.brown", "action": "Generated UFT script for Login Form"}
    ]
    return pd.DataFrame(activities)

def get_execution_summary():
    """Get summary of recent test executions"""
    return {
        "total": 120,
        "passed": 98,
        "failed": 15,
        "blocked": 7,
        "last_run": "2025-04-26 08:45:11",
        "run_by": "jane.smith",
        "duration": "1h 15m"
    }

def get_defect_summary():
    """Get summary of defects"""
    return {
        "total": 34,
        "open": 12,
        "in_progress": 8,
        "closed": 14,
        "critical": 3,
        "high": 7,
        "medium": 15,
        "low": 9
    }

def get_execution_trend_data():
    """Get trend data for test executions over time"""
    # Generate demo data for the past 7 days
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7, 0, -1)]
    
    data = []
    for date in dates:
        total = random.randint(100, 150)
        passed = random.randint(70, total - 20)
        failed = random.randint(5, 20)
        blocked = total - passed - failed
        
        data.append({"date": date, "status": "Passed", "count": passed})
        data.append({"date": date, "status": "Failed", "count": failed})
        data.append({"date": date, "status": "Blocked", "count": blocked})
    
    return pd.DataFrame(data)

def render_dashboard():
    """Render the dashboard/home screen"""
    st.markdown("<h2 class='sub-header'>Dashboard</h2>", unsafe_allow_html=True)
    
    # Quick Actions Row
    st.subheader("Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🧪 Generate Tests from Requirements", use_container_width=True):
            st.session_state.current_page = "TestGeneration"
    
    with col2:
        if st.button("📝 Review Existing Test Case", use_container_width=True):
            st.session_state.current_page = "Repository"
    
    with col3:
        if st.button("▶️ View Execution Runs", use_container_width=True):
            st.session_state.current_page = "Execution"
    
    with col4:
        if st.button("🔍 Analyze Failed Test", use_container_width=True):
            st.session_state.current_page = "Analysis"
    
    # Main Dashboard Content
    col_left, col_right = st.columns([2, 1])
    
    # Left Column - Summaries and Charts
    with col_left:
        # Test Execution Summary
        with st.container():
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Test Execution Summary")
            
            exec_summary = get_execution_summary()
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Tests", exec_summary["total"])
            col2.metric("Passed", exec_summary["passed"], f"{exec_summary['passed'] / exec_summary['total'] * 100:.1f}%")
            col3.metric("Failed", exec_summary["failed"], f"{exec_summary['failed'] / exec_summary['total'] * 100:.1f}%")
            col4.metric("Blocked", exec_summary["blocked"], f"{exec_summary['blocked'] / exec_summary['total'] * 100:.1f}%")
            
            st.caption(f"Last Run: {exec_summary['last_run']} by {exec_summary['run_by']} (Duration: {exec_summary['duration']})")
            
            # Add execution trend chart
            st.subheader("7-Day Execution Trend")
            trend_data = get_execution_trend_data()
            
            chart = alt.Chart(trend_data).mark_bar().encode(
                x=alt.X('date:N', title='Date'),
                y=alt.Y('count:Q', title='Count'),
                color=alt.Color('status:N', scale=alt.Scale(
                    domain=['Passed', 'Failed', 'Blocked'],
                    range=['#27ae60', '#e74c3c', '#f39c12']
                )),
                tooltip=['date', 'status', 'count']
            ).properties(height=250)
            
            st.altair_chart(chart, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Defect Summary
        with st.container():
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Defect Summary")
            
            defect_summary = get_defect_summary()
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Defects", defect_summary["total"])
            col2.metric("Open", defect_summary["open"])
            col3.metric("In Progress", defect_summary["in_progress"])
            col4.metric("Closed", defect_summary["closed"])
            
            # Defect severity breakdown
            st.subheader("Defect Severity Breakdown")
            severity_data = pd.DataFrame({
                'Severity': ['Critical', 'High', 'Medium', 'Low'],
                'Count': [
                    defect_summary["critical"],
                    defect_summary["high"],
                    defect_summary["medium"],
                    defect_summary["low"]
                ]
            })
            
            chart = alt.Chart(severity_data).mark_bar().encode(
                x=alt.X('Count:Q', title='Count'),
                y=alt.Y('Severity:N', title='Severity', sort='-x'),
                color=alt.Color('Severity:N', scale=alt.Scale(
                    domain=['Critical', 'High', 'Medium', 'Low'],
                    range=['#e74c3c', '#f39c12', '#3498db', '#27ae60']
                )),
                tooltip=['Severity', 'Count']
            ).properties(height=200)
            
            st.altair_chart(chart, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Right Column - Tasks and Activities
    with col_right:
        # Pending Tasks
        with st.container():
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Pending Tasks")
            
            tasks_df = get_pending_tasks()
            
            # Color the priority
            def color_priority(val):
                if val == "High":
                    return "background-color: #ffcccc"
                elif val == "Medium":
                    return "background-color: #ffffcc"
                else:
                    return "background-color: #ccffcc"
            
            st.dataframe(
                tasks_df.style.applymap(color_priority, subset=['priority']),
                height=300,
                use_container_width=True
            )
            
            if st.button("View All Tasks", use_container_width=True):
                # This would link to a full task view
                st.info("Task view not implemented in this demo")
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Recent Activity
        with st.container():
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Recent Activity")
            
            activities_df = get_recent_activity()
            
            for _, row in activities_df.iterrows():
                st.markdown(f"""
                <div style="margin-bottom: 10px; padding: 5px; border-bottom: 1px solid #eee;">
                    <small>{row['timestamp']}</small><br/>
                    <strong>{row['user']}</strong>: {row['action']}
                </div>
                """, unsafe_allow_html=True)
                
            if st.button("View All Activity", use_container_width=True):
                # This would link to a full activity log
                st.info("Activity log not implemented in this demo")
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Bottom section with announcements or additional insights
    with st.container():
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("System Announcements")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info("📢 watsonx IPG Testing Platform v2.0 has been released with UFT code generation capabilities!")
        with col2:
            st.warning("⚠️ ALM connection is operating in limited capacity. Full functionality expected to resume by April 28.")
        
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    # For standalone testing
    st.set_page_config(page_title="Dashboard - Watsonx IPG Testing", layout="wide")
    
    # Add custom CSS for standalone mode
    st.markdown("""
    <style>
        .main-header { font-size: 2.5rem; color: #0063B2; margin-bottom: 1rem; }
        .sub-header { font-size: 1.5rem; color: #444; margin-bottom: 1rem; }
        .card { padding: 1.5rem; border-radius: 0.5rem; background-color: #f8f9fa; 
                box-shadow: 0 0.15rem 0.5rem rgba(0, 0, 0, 0.1); margin-bottom: 1rem; }
    </style>
    """, unsafe_allow_html=True)
    
    render_dashboard()