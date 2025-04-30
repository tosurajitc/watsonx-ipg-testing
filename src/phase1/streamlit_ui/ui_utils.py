import streamlit as st
import pandas as pd
import base64
import io
import json
import xml.dom.minidom
import plotly.express as px
import plotly.graph_objs as go
from typing import Any, Dict, List, Optional, Union


#################### Testing blocl



################### Testing block endss here


class UIUtils:
    """
    Comprehensive UI utility functions for data formatting, conversion, and display
    """

    @staticmethod
    def format_data_display(
        data: Union[pd.DataFrame, Dict, List], 
        display_type: str = 'table',
        max_rows: int = 10
    ) -> None:
        """
        Format and display data in various styles
        
        Args:
            data (Union[pd.DataFrame, Dict, List]): Data to display
            display_type (str): Display method ('table', 'json', 'raw')
            max_rows (int): Maximum rows to display
        """
        # Convert input to DataFrame if needed
        if isinstance(data, dict):
            df = pd.DataFrame([data])
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            st.warning("Unsupported data type")
            return
        
        # Limit rows
        df = df.head(max_rows)
        
        # Display based on type
        if display_type == 'table':
            st.dataframe(df)
        elif display_type == 'json':
            st.json(df.to_dict(orient='records'))
        else:
            st.write(df)

    @staticmethod
    def convert_file_preview(
        uploaded_file: Any, 
        file_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert and preview different file types
        
        Args:
            uploaded_file (Any): Streamlit uploaded file
            file_type (Optional[str]): Explicit file type
        
        Returns:
            Dict with file details and preview
        """
        if not uploaded_file:
            return {"error": "No file uploaded"}
        
        # Determine file type
        if not file_type:
            file_type = uploaded_file.name.split('.')[-1].lower()
        
        try:
            # CSV Preview
            if file_type in ['csv', 'txt']:
                df = pd.read_csv(uploaded_file)
                return {
                    "type": "csv",
                    "dataframe": df,
                    "preview": df.head(),
                    "shape": df.shape
                }
            
            # Excel Preview
            elif file_type in ['xlsx', 'xls']:
                df = pd.read_excel(uploaded_file)
                return {
                    "type": "excel",
                    "dataframe": df,
                    "preview": df.head(),
                    "shape": df.shape
                }
            
            # JSON Preview
            elif file_type == 'json':
                json_data = json.load(uploaded_file)
                return {
                    "type": "json",
                    "data": json_data,
                    "preview": json.dumps(json_data, indent=2)
                }
            
            # XML Preview
            elif file_type == 'xml':
                xml_content = uploaded_file.getvalue().decode('utf-8')
                # Pretty print XML
                parsed_xml = xml.dom.minidom.parseString(xml_content)
                pretty_xml = parsed_xml.toprettyxml(indent="  ")
                return {
                    "type": "xml",
                    "content": xml_content,
                    "preview": pretty_xml
                }
            
            # Plain text preview
            else:
                text_content = uploaded_file.getvalue().decode('utf-8')
                return {
                    "type": "text",
                    "content": text_content,
                    "preview": text_content[:500] + "..." if len(text_content) > 500 else text_content
                }
        
        except Exception as e:
            return {"error": f"Error processing file: {str(e)}"}

    @staticmethod
    def create_download_button(
        data: Union[pd.DataFrame, Dict, List, str], 
        filename: str, 
        file_type: str = 'csv'
    ) -> str:
        """
        Create a download button for various data types
        
        Args:
            data (Union[pd.DataFrame, Dict, List, str]): Data to download
            filename (str): Name of the file to download
            file_type (str): File type for download
        
        Returns:
            Base64 encoded download link
        """
        # Convert data to appropriate format
        if isinstance(data, pd.DataFrame):
            if file_type == 'csv':
                binary_output = data.to_csv(index=False).encode()
                mime_type = 'text/csv'
            elif file_type == 'xlsx':
                output = io.BytesIO()
                data.to_excel(output, index=False)
                binary_output = output.getvalue()
                mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif isinstance(data, (dict, list)):
            binary_output = json.dumps(data, indent=2).encode()
            mime_type = 'application/json'
        elif isinstance(data, str):
            binary_output = data.encode()
            mime_type = 'text/plain'
        else:
            raise ValueError("Unsupported data type for download")
        
        # Encode for download
        b64 = base64.b64encode(binary_output).decode()
        
        # Create download link
        href = f'<a href="data:{mime_type};base64,{b64}" download="{filename}.{file_type}">Download {filename}.{file_type}</a>'
        return href

    @staticmethod
    def create_plotly_chart(
        data: pd.DataFrame, 
        x_column: str, 
        y_column: str, 
        chart_type: str = 'bar',
        title: Optional[str] = None
    ) -> go.Figure:
        """
        Create a Plotly chart with consistent styling
        
        Args:
            data (pd.DataFrame): Data for the chart
            x_column (str): Column for x-axis
            y_column (str): Column for y-axis
            chart_type (str): Type of chart ('bar', 'line', 'scatter')
            title (Optional[str]): Chart title
        
        Returns:
            Plotly Figure object
        """
        # Chart type mapping
        chart_functions = {
            'bar': px.bar,
            'line': px.line,
            'scatter': px.scatter
        }
        
        # Select chart function
        chart_func = chart_functions.get(chart_type, px.bar)
        
        # Create figure
        fig = chart_func(
            data, 
            x=x_column, 
            y=y_column, 
            title=title or f"{chart_type.capitalize()} Chart"
        )
        
        # Consistent styling
        fig.update_layout(
            title_font_size=16,
            title_x=0.5,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family="Arial, sans-serif", size=12),
        )
        
        return fig

    @staticmethod
    def display_notification(
        message: str, 
        type: str = 'info', 
        icon: Optional[str] = None
    ) -> None:
        """
        Display a styled notification
        
        Args:
            message (str): Notification message
            type (str): Notification type (info, success, warning, error)
            icon (Optional[str]): Optional icon to display
        """
        # Notification type styling
        notification_styles = {
            'info': ('ℹ️', 'blue'),
            'success': ('✅', 'green'),
            'warning': ('⚠️', 'orange'),
            'error': ('❌', 'red')
        }
        
        # Get icon and color
        default_icon, color = notification_styles.get(type, ('🔔', 'blue'))
        display_icon = icon or default_icon
        
        # Render notification
        st.markdown(f"""
        <div style="
            background-color: {color}10; 
            color: {color}; 
            border-left: 4px solid {color}; 
            padding: 10px; 
            border-radius: 5px; 
            margin-bottom: 10px;
        ">
            <span style="margin-right: 10px;">{display_icon}</span>
            {message}
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def layout_columns(
        num_columns: int, 
        equal_width: bool = True, 
        gap: str = 'small'
    ) -> List[Any]:
        """
        Create consistent column layouts
        
        Args:
            num_columns (int): Number of columns to create
            equal_width (bool): Whether columns should have equal width
            gap (str): Gap between columns ('small', 'medium', 'large')
        
        Returns:
            List of Streamlit column objects
        """
        # Column width configuration
        if equal_width:
            columns = st.columns(num_columns)
        else:
            # Example of variable width columns
            column_widths = [1] * num_columns
            column_widths[0] = 2  # First column wider
            columns = st.columns(column_widths)
        
        return columns

def main():
    """
    Demonstrate UI utility functions
    """
    st.title("UI Utilities Demonstration")
    
    # Data Display
    st.header("Data Display")
    sample_data = [
        {"name": "Alice", "age": 30, "city": "New York"},
        {"name": "Bob", "age": 25, "city": "San Francisco"}
    ]
    UIUtils.format_data_display(sample_data)
    
    # File Preview
    st.header("File Preview")
    uploaded_file = st.file_uploader("Upload a file")
    if uploaded_file:
        preview = UIUtils.convert_file_preview(uploaded_file)
        st.json(preview)
    
    # Download Button
    st.header("Download Button")
    df = pd.DataFrame({
        'Name': ['Alice', 'Bob'],
        'Age': [30, 25]
    })
    download_link = UIUtils.create_download_button(df, 'sample_data')
    st.markdown(download_link, unsafe_allow_html=True)
    
    # Plotly Chart
    st.header("Plotly Chart")
    chart_data = pd.DataFrame({
        'Category': ['A', 'B', 'C', 'D'],
        'Value': [10, 20, 15, 25]
    })
    fig = UIUtils.create_plotly_chart(chart_data, 'Category', 'Value')
    st.plotly_chart(fig)
    
    # Notifications
    st.header("Notifications")
    notification_types = ['info', 'success', 'warning', 'error']
    for ntype in notification_types:
        UIUtils.display_notification(
            f"This is a {ntype.capitalize()} notification", 
            type=ntype
        )
    
    # Layout Columns
    st.header("Column Layouts")
    columns = UIUtils.layout_columns(3)
    with columns[0]:
        st.write("Column 1")
    with columns[1]:
        st.write("Column 2")
    with columns[2]:
        st.write("Column 3")

if __name__ == "__main__":
    main()