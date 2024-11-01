import unittest
import os
import json
import tempfile
import streamlit as st
from unittest.mock import patch, MagicMock
from side_bar_state_mgr import SideBarStateMgr  

class MockSessionState(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(f"'MockSessionState' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError(f"'MockSessionState' object has no attribute '{name}'")

class TestSideBarStateMgr(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for test states
        self.temp_dir = tempfile.mkdtemp()
        self.old_saved_states_dir = SideBarStateMgr.saved_states_dir
        SideBarStateMgr.saved_states_dir = self.temp_dir
        
        # Mock streamlit's session_state
        self.mock_session_state = MockSessionState()
        self.patcher = patch('streamlit.session_state', self.mock_session_state)
        self.patcher.start()

    def tearDown(self):
        # Remove the temporary directory after tests
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)
        
        # Restore the original saved_states_dir
        SideBarStateMgr.saved_states_dir = self.old_saved_states_dir
        
        # Stop the patcher
        self.patcher.stop()

    def test_save_state(self):
        key_storage_map  = { 'persistant' : ['count', 'name'], 'volatile' : ['vol_*']}
        self.mock_session_state['count'] = 5
        self.mock_session_state['name'] = 'Test'
        
        SideBarStateMgr.save_state('test_state', key_storage_map )
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, 'test_state.json')))

    def test_load_state(self):
        test_state = {'count': 10, 'name': 'LoadTest'}
        with open(os.path.join(self.temp_dir, 'test_load.json'), 'w') as f:
            json.dump(test_state, f)
        
        key_storage_map  = { 'persistant' : ['count', 'name'], 'volatile' : ['vol_*']}
        loaded_state = SideBarStateMgr.load_state('test_load', key_storage_map )
        self.assertEqual(loaded_state, test_state)

    @patch('streamlit.session_state', {})
    def test_set_session_state(self):
        # Define test data
        key_storage_map = {
            'persistant': ['persist_*', 'keep_me'],
            'volatile': ['temp_*', 'clear_me']
        }
        loaded_state = {
            'persist_1': 'value1',
            'keep_me': 'value2',
            'new_key': 'value3'
        }

        # Set up initial session state
        st.session_state.update({
            'persist_1': 'old_value1',
            'keep_me': 'old_value2',
            'temp_1': 'temp_value1',
            'clear_me': 'clear_value',
            'non_volatile': 'keep_this'
        })

        # Call the method
        SideBarStateMgr.set_session_state(key_storage_map, loaded_state)

        # Assert the results
        self.assertEqual(st.session_state, {
            'persist_1': 'value1',
            'keep_me': 'value2',
            'new_key': 'value3',
            'non_volatile': 'keep_this'
        })

    @patch.object(SideBarStateMgr, 'key_is_persistant')
    @patch.object(SideBarStateMgr, 'key_is_volatile')
    def test_set_session_state_calls(self, mock_is_volatile, mock_is_persistant):
        key_storage_map = {'persistant': [], 'volatile': []}
        loaded_state = {'key1': 'value1'}
        
        # Set up the mocks
        mock_is_persistant.side_effect = [True, False, False]
        mock_is_volatile.side_effect = [False, True, False]

        with patch('streamlit.session_state', {'key1': 'old1', 'key2': 'old2', 'key3': 'old3'}):
            SideBarStateMgr.set_session_state(key_storage_map, loaded_state)

        # Assert the mocks were called correctly
        self.assertEqual(mock_is_persistant.call_count, 3)
        self.assertEqual(mock_is_volatile.call_count, 2)
        mock_is_persistant.assert_any_call('key1', key_storage_map)
        mock_is_persistant.assert_any_call('key2', key_storage_map)
        mock_is_persistant.assert_any_call('key3', key_storage_map)

    def test_get_saved_states(self):
        # Create some test state files
        open(os.path.join(self.temp_dir, 'state1.json'), 'w').close()
        open(os.path.join(self.temp_dir, 'state2.json'), 'w').close()
        
        states = SideBarStateMgr.get_saved_states()
        self.assertEqual(set(states), {'state1', 'state2'})

    def test_delete_state(self):
        # Create a test state file
        test_file = os.path.join(self.temp_dir, 'test_delete.json')
        open(test_file, 'w').close()
        
        SideBarStateMgr.delete_state('test_delete')
        self.assertFalse(os.path.exists(test_file))

    def test_rename_state(self):
        # Create a test state file
        old_file = os.path.join(self.temp_dir, 'old_name.json')
        new_file = os.path.join(self.temp_dir, 'new_name.json')
        open(old_file, 'w').close()
        
        SideBarStateMgr.rename_state('old_name', 'new_name')
        self.assertFalse(os.path.exists(old_file))
        self.assertTrue(os.path.exists(new_file))

    def test_set_status_message(self):
        SideBarStateMgr.set_status_message('Test message', 'success')
        self.assertEqual(self.mock_session_state['sbsm_status_message'], 'Test message')
        self.assertEqual(self.mock_session_state.sbsm_status_message, 'Test message')
        self.assertEqual(self.mock_session_state['sbsm_status_type'], 'success')
        self.assertEqual(self.mock_session_state.sbsm_status_type, 'success')

    def test_show_status_message(self):
        self.mock_session_state.sbsm_status_message = 'Test message'
        self.mock_session_state.sbsm_status_type = 'success'
        
        with patch('streamlit.sidebar.success') as mock_success:
            SideBarStateMgr.show_status_message()
            
            mock_success.assert_called_once_with('Test message')
            self.assertNotIn('sbsm_status_message', self.mock_session_state)
            self.assertNotIn('sbsm_status_type', self.mock_session_state)
            
            with self.assertRaises(AttributeError):
                _ = self.mock_session_state.sbsm_status_message
            with self.assertRaises(AttributeError):
                _ = self.mock_session_state.sbsm_status_type

    @patch('streamlit.sidebar.button')
    @patch('streamlit.sidebar.columns')
    @patch('streamlit.sidebar.write')
    def test_setup_sidebar(self, mock_write, mock_columns, mock_button):
        mock_button.return_value = False
        mock_columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        
        # Create a test state file to ensure the columns are called
        open(os.path.join(self.temp_dir, 'test_state.json'), 'w').close()
        
        SideBarStateMgr.setup_sidebar(['count'])
        
        mock_button.assert_called()
        mock_write.assert_called_with(SideBarStateMgr.STRINGS['SAVED_STATES'])
        mock_columns.assert_called()

    def test_save_current_state(self):
        key_storage_map  = { 'persistant' : ['count'], 'volatile' : []}
        state_manager = SideBarStateMgr(key_storage_map )
        self.mock_session_state['count'] = 5
        
        with patch('side_bar_state_mgr.SideBarStateMgr.save_state') as mock_save:
            state_manager.save_current_state()
            mock_save.assert_called_once_with(SideBarStateMgr.STRINGS['DEFAULT_STATE'], key_storage_map )

    def test_init(self):
        key_storage_map  = { 'persistant' : ['count'], 'volatile' : []}
        self.mock_session_state['sbsm_state_to_load'] = 'test_state'
        self.mock_session_state['count'] = 5

        with patch('side_bar_state_mgr.SideBarStateMgr.load_state', return_value={'count': 10}):
            with patch('side_bar_state_mgr.SideBarStateMgr.set_status_message') as mock_set_status:
                with patch('side_bar_state_mgr.SideBarStateMgr.setup_sidebar') as mock_setup_sidebar:
                    state_manager = SideBarStateMgr(key_storage_map )

                    self.assertEqual(self.mock_session_state['count'], 10)
                    self.assertEqual(self.mock_session_state['sbsm_current_state'], 'test_state')
                    mock_set_status.assert_called_once_with(SideBarStateMgr.STRINGS['STATE_LOADED'].format('test_state'))
                    mock_setup_sidebar.assert_called_once_with(key_storage_map )

    def test_strings(self):
        # Test that all required strings are present in the STRINGS dictionary
        required_strings = [
            'CREATE_NEW_STATE', 'NEW_STATE_BASENAME', 'SAVED_STATES', 'CONFIRM_RENAME', 'CANCEL_RENAME',
            'RENAME', 'DELETE', 'STATE_CREATED', 'STATE_RENAMED', 'STATE_DELETED',
            'STATE_LOADED', 'DEFAULT_STATE'
        ]
        for string in required_strings:
            self.assertIn(string, SideBarStateMgr.STRINGS)


    def test_wildcard_match(self):
        patterns = ['prefix_*', 'exact_match', 'another_prefix_*']
        
        # Should match
        self.assertTrue(SideBarStateMgr.key_matches_patterns('prefix_something', patterns))
        self.assertTrue(SideBarStateMgr.key_matches_patterns('exact_match', patterns))
        self.assertTrue(SideBarStateMgr.key_matches_patterns('another_prefix_test', patterns))
        
        # Should not match
        self.assertFalse(SideBarStateMgr.key_matches_patterns('not_matching', patterns))
        self.assertFalse(SideBarStateMgr.key_matches_patterns('prefix', patterns))
        self.assertFalse(SideBarStateMgr.key_matches_patterns('exact_match_with_extra', patterns))

    def test_save_and_load_state(self):
        # Mock st.session_state
        st.session_state = {
            'prefix_1': 'value1',
            'prefix_2': 'value2',
            'other_key': 'value3',
            'exact_match': 'value4'
        }

        key_storage_map  = { 'persistant' : ['prefix_*', 'exact_match'], 'volatile' : []}
        
        # Test save_state
        SideBarStateMgr.save_state('test', key_storage_map )
        
        # Test load_state
        loaded_state = SideBarStateMgr.load_state('test', key_storage_map )
        
        self.assertEqual(loaded_state, {
            'prefix_1': 'value1',
            'prefix_2': 'value2',
            'exact_match': 'value4'
        })
        self.assertNotIn('other_key', loaded_state)

if __name__ == '__main__':
    unittest.main()