""" Displays and allows download of objects as json, stores state in streamlit """
import sys
import math
import json
import base64
import streamlit as st


class JSONViewer:
    """ Handles viewing and downloading of objects as JSON """

    state_key = 'json_viewer_data_key'

    @staticmethod
    def get_size(obj, seen=None):
        """Recursively calculate size of objects"""

        size = sys.getsizeof(obj)
        if seen is None:
            seen = set()
        obj_id = id(obj)
        if obj_id in seen:
            return 0

        # Important mark as seen *before* entering recursion to gracefully handle
        # self-referential objects
        seen.add(obj_id)
        if isinstance(obj, dict):
            size += sum([JSONViewer.get_size(v, seen) for v in obj.values()])
            size += sum([JSONViewer.get_size(k, seen) for k in obj.keys()])
        elif hasattr(obj, '__dict__'):
            size += JSONViewer.get_size(obj.__dict__, seen)
        elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
            size += sum([JSONViewer.get_size(i, seen) for i in obj])
        return size

    @staticmethod
    def convert_size(size_bytes):
        """Convert size in bytes to a more readable format"""
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    def run(self):
        """ Show the JSON """
        json_data = st.session_state.get(self.state_key)
        if json_data:

            # Back button
            if st.button("Done"):
                del st.session_state[self.state_key]
                st.rerun()

            # Size
            size_bytes = JSONViewer.get_size(json_data)
            size_bytes_str = JSONViewer.convert_size(size_bytes)
            st.write(f"Size: {size_bytes_str}")

            # Download button
            self.add_download_button(json_data)

            # Show the json
            st.json(json_data)

            return True
        return False

    def add_download_button(self, json_data):
        """ Serialse, base64 encode and make available for download """

        class CustomJSONEncoder(json.JSONEncoder):
            """ Customer encoder to handle non serializable objects"""
            def default(self, o):
                try:
                    return super().default(o)
                except TypeError:
                    return "<data removed - not serializable>"

        def safe_json_dumps(data, indent=2):
            return json.dumps(data, indent=indent, cls=CustomJSONEncoder)

        json_string = safe_json_dumps(json_data, indent=2)
        b64 = base64.b64encode(json_string.encode()).decode()
        href = f'<a href="data:file/json;base64,{b64}" download="data.json">Download</a>'
        st.markdown(href, unsafe_allow_html=True)

    @staticmethod
    def view_json(data):
        """ Set up the state with the data, then trigger rerun to display"""
        st.session_state[JSONViewer.state_key] = dict(data)
        st.rerun()

def example_usage():
    """ Usage illustration """

    # Example usage
    st.title("Example Viewer")

    # Check if we should display the JSON viewer
    json_viewer = JSONViewer()
    if json_viewer.run():
        return

    default_data = {
        "name": "John Doe",
        "age": 30,
        "city": "New York",
        "hobbies": ["reading", "swimming", "cycling"]
    }
    default_json = json.dumps(default_data, indent=2)


    # Prompt for JSON to display
    json_input = st.text_area("Enter your JSON data here:", value=default_json, height=300)

    if st.button("View JSON"):
        try:
            data = json.loads(json_input)
            JSONViewer.view_json(data)

        except json.JSONDecodeError:
            st.error("Invalid JSON format. Please check your input.")

if __name__ == "__main__":
    example_usage()
