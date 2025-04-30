import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional, Callable
import base64



#################### Testing blocl



################### Testing block endss here



class SharedComponents:
    """
    A collection of shared UI components for consistent styling and functionality
    """
    
    @staticmethod
    def info_card(title: str, 
                  content: str, 
                  icon: Optional[str] = None, 
                  color: str = "blue") -> None:
        """
        Create an informational card with consistent styling
        
        Args:
            title (str): Card title
            content (str): Card content/description
            icon (Optional[str]): Optional icon name (e.g., 'info', 'warning')
            color (str): Color scheme for the card
        """
        # Color mapping for different card types
        color_map = {
            "blue": "#E6F2FF",
            "green": "#E6F9F0",
            "yellow": "#FFF9E6",
            "red": "#FFE6E6"
        }
        
        # Ensure color is valid
        bg_color = color_map.get(color, color_map["blue"])
        
        st.markdown(f"""
        <div style="
            background-color: {bg_color};
            border-left: 4px solid {'#1E90FF' if color == 'blue' else '#4CAF50' if color == 'green' else '#FFC107' if color == 'yellow' else '#F44336'};
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
        ">
            <h4 style="margin-top: 0; margin-bottom: 10px; color: #333;">
                {title}
            </h4>
            <p style="margin-bottom: 0; color: #666;">
                {content}
            </p>
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def status_indicator(status: str, 
                         message: Optional[str] = None) -> None:
        """
        Create a status indicator with color-coded display
        
        Args:
            status (str): Status type ('success', 'warning', 'error', 'info')
            message (Optional[str]): Optional status message
        """
        status_colors = {
            "success": "green",
            "warning": "orange", 
            "error": "red",
            "info": "blue"
        }
        
        color = status_colors.get(status.lower(), "gray")
        
        st.markdown(f"""
        <div style="
            display: flex;
            align-items: center;
            padding: 10px;
            background-color: {'#E6F9F0' if status == 'success' else '#FFF9E6' if status == 'warning' else '#FFE6E6' if status == 'error' else '#E6F2FF'};
            border-left: 4px solid {color};
            border-radius: 5px;
            margin-bottom: 10px;
        ">
            <span style="
                height: 10px;
                width: 10px;
                background-color: {color};
                border-radius: 50%;
                display: inline-block;
                margin-right: 10px;
            "></span>
            <span style="color: #333;">
                {message or status.capitalize()}
            </span>
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def advanced_file_uploader(
        label: str, 
        file_types: List[str] = None, 
        key: Optional[str] = None,
        multiple: bool = False
    ) -> Any:
        """
        Create an advanced file uploader with additional styling and validation
        
        Args:
            label (str): Uploader label
            file_types (List[str]): Allowed file types
            key (Optional[str]): Unique key for the uploader
            multiple (bool): Allow multiple file uploads
        
        Returns:
            Uploaded file object(s)
        """
        # Default file types if not specified
        if file_types is None:
            file_types = ['csv', 'xlsx', 'xls', 'txt', 'json', 'xml', 'pdf', 'docx']
        
        # File uploader with extended functionality
        uploaded_file = st.file_uploader(
            label, 
            type=file_types, 
            accept_multiple_files=multiple,
            key=key
        )
        
        # Optional additional validation or preview
        if uploaded_file:
            # For single file
            if not multiple and uploaded_file:
                file_details = {
                    "Filename": uploaded_file.name,
                    "Filetype": uploaded_file.type,
                    "Filesize": f"{uploaded_file.size / 1024:.2f} KB"
                }
                st.json(file_details)
            
            # For multiple files
            elif multiple and uploaded_file:
                st.write(f"Uploaded {len(uploaded_file)} files")
                for file in uploaded_file:
                    st.write(f"- {file.name}")
        
        return uploaded_file

    @staticmethod
    def progress_bar(
        value: float, 
        label: Optional[str] = None, 
        color: str = "#1E90FF"
    ) -> None:
        """
        Create a styled progress bar
        
        Args:
            value (float): Progress value (0.0 to 1.0)
            label (Optional[str]): Optional label for the progress bar
            color (str): Color of the progress bar
        """
        # Ensure value is between 0 and 1
        value = max(0.0, min(1.0, value))
        
        st.markdown(f"""
        <div style="
            width: 100%;
            background-color: #f0f0f0;
            border-radius: 5px;
            margin-bottom: 10px;
        ">
            <div style="
                width: {value * 100}%;
                background-color: {color};
                height: 20px;
                border-radius: 5px;
                transition: width 0.5s ease-in-out;
            ">
                <span style="
                    color: white;
                    padding-left: 10px;
                    line-height: 20px;
                    font-size: 12px;
                ">
                    {f"{label} " if label else ''}{f"{value * 100:.1f}%"}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def advanced_dataframe(
        data: pd.DataFrame, 
        title: Optional[str] = None,
        editable: bool = False,
        download: bool = True
    ) -> None:
        """
        Create an advanced dataframe display with additional features
        
        Args:
            data (pd.DataFrame): DataFrame to display
            title (Optional[str]): Optional title for the dataframe
            editable (bool): Allow inline editing
            download (bool): Allow CSV/Excel download
        """
        # Display title if provided
        if title:
            st.markdown(f"### {title}")
        
        # Dataframe display
        df = st.data_editor(
            data, 
            disabled=not editable,
            use_container_width=True
        )
        
        # Download options
        if download:
            col1, col2 = st.columns(2)
            
            with col1:
                # CSV Download
                csv = df.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="dataframe.csv">Download CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
            
            with col2:
                # Excel Download
                excel = df.to_excel(index=False)
                b64 = base64.b64encode(excel).decode()
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="dataframe.xlsx">Download Excel</a>'
                st.markdown(href, unsafe_allow_html=True)

    @staticmethod
    def form_input(
        label: str, 
        input_type: str = 'text', 
        key: Optional[str] = None,
        help_text: Optional[str] = None,
        required: bool = False,
        default_value: Any = None,
        options: Optional[List[str]] = None
    ) -> Any:
        """
        Create a standardized form input with consistent styling
        
        Args:
            label (str): Input label
            input_type (str): Type of input (text, number, select, etc.)
            key (Optional[str]): Unique key for the input
            help_text (Optional[str]): Additional help text
            required (bool): Whether the field is required
            default_value (Any): Default value for the input
            options (Optional[List[str]]): Options for select inputs
        
        Returns:
            Input value
        """
        # Input type mapping
        if input_type == 'text':
            return st.text_input(
                label, 
                key=key, 
                help=help_text, 
                value=default_value,
                placeholder=f"{'Enter ' + label + (' (Required)' if required else '')}" 
            )
        
        elif input_type == 'number':
            return st.number_input(
                label, 
                key=key, 
                help=help_text, 
                value=default_value or 0,
                min_value=0
            )
        
        elif input_type == 'select':
            return st.selectbox(
                label, 
                options=options or [], 
                key=key, 
                help=help_text,
                index=0 if default_value and default_value in options else None
            )
        
        elif input_type == 'textarea':
            return st.text_area(
                label, 
                key=key, 
                help=help_text, 
                value=default_value,
                placeholder=f"{'Enter ' + label + (' (Required)' if required else '')}"
            )
        
        elif input_type == 'date':
            return st.date_input(
                label, 
                key=key, 
                help=help_text, 
                value=default_value
            )
        
        else:
            st.warning(f"Unsupported input type: {input_type}")
            return None

def main():
    """
    Demonstration of shared components
    """
    st.title("Shared UI Components Demo")
    
    # Info Card Demo
    st.header("Info Card")
    SharedComponents.info_card(
        "Welcome", 
        "This is a demo of our shared UI components.", 
        color="blue"
    )
    
    # Status Indicator Demo
    st.header("Status Indicators")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        SharedComponents.status_indicator("success", "Operation Successful")
    with col2:
        SharedComponents.status_indicator("warning", "Proceed with Caution")
    with col3:
        SharedComponents.status_indicator("error", "Critical Error")
    with col4:
        SharedComponents.status_indicator("info", "Information")
    
    # File Uploader Demo
    st.header("File Uploader")
    uploaded_file = SharedComponents.advanced_file_uploader(
        "Upload Test Data", 
        file_types=['csv', 'xlsx']
    )
    
    # Progress Bar Demo
    st.header("Progress Bar")
    SharedComponents.progress_bar(0.65, "Test Execution Progress")
    
    # Advanced DataFrame Demo
    st.header("Advanced DataFrame")
    sample_data = pd.DataFrame({
        'Name': ['John', 'Jane', 'Bob'],
        'Age': [30, 25, 35],
        'City': ['New York', 'San Francisco', 'Chicago']
    })
    SharedComponents.advanced_dataframe(
        sample_data, 
        title="Sample Employee Data"
    )
    
    # Form Input Demo
    st.header("Form Inputs")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        name = SharedComponents.form_input(
            "Name", 
            input_type='text', 
            required=True
        )
    
    with col2:
        age = SharedComponents.form_input(
            "Age", 
            input_type='number'
        )
    
    with col3:
        city = SharedComponents.form_input(
            "City", 
            input_type='select', 
            options=['New York', 'San Francisco', 'Chicago']
        )

if __name__ == "__main__":
    main()