"""
Google Sheets Manager for task management integration.

This module handles all interactions with Google Sheets API for task tracking:
- Adding new tasks with auto-incrementing task IDs
- Retrieving tasks with filtering and sorting
- Updating task outcomes
- Merging cells for proper formatting (Description column spans C-F)

The manager supports:
- Custom header row placement (default: row 6)
- Merged Description column (C-F)
- Automatic cell merging after task creation
- Error handling and logging
"""

import logging
import os
from typing import List, Dict, Optional
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from google.auth.exceptions import GoogleAuthError

logger = logging.getLogger(__name__)


class GoogleSheetsManager:
    """Manages Google Sheets operations for task tracking."""
    
    # Define the scope for Google Sheets API
    SCOPE = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Column headers for the sheet
    HEADERS = [
        "Task ID",
        "Status",
        "Description",
        "Assigned to",
        "Start Date",
        "End Date",
        "Measurable Outcome",
        "Actual Outcome"
    ]
    
    def __init__(self, spreadsheet_id: str, credentials_path: str = "credentials.json", header_row: int = 6):
        """
        Initialize the Google Sheets Manager.
        
        Args:
            spreadsheet_id: The ID of the Google Spreadsheet
            credentials_path: Path to the service account credentials JSON file
            header_row: Row number where headers are located (default: 6)
        """
        self.spreadsheet_id = spreadsheet_id
        self.credentials_path = credentials_path
        self.header_row = header_row
        self.client: Optional[gspread.Client] = None
        self.spreadsheet: Optional[gspread.Spreadsheet] = None
        self.worksheet: Optional[gspread.Worksheet] = None
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Google Sheets client with service account credentials."""
        try:
            if not os.path.exists(self.credentials_path):
                raise FileNotFoundError(
                    f"Credentials file not found: {self.credentials_path}\n"
                    "Please download your service account credentials and save as 'credentials.json'"
                )
            
            # Load credentials from service account file
            creds = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.SCOPE
            )
            
            # Create gspread client
            self.client = gspread.authorize(creds)
            
            # Open the spreadsheet
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            
            # Get or create the first worksheet
            try:
                self.worksheet = self.spreadsheet.sheet1
            except Exception:
                # Create new worksheet if it doesn't exist
                self.worksheet = self.spreadsheet.add_worksheet(
                    title="Tasks",
                    rows=1000,
                    cols=10
                )
            
            # Ensure headers exist
            self._ensure_headers()
            
            logger.info(f"Successfully connected to Google Sheet: {self.spreadsheet.title}")
            
        except FileNotFoundError as e:
            logger.error(f"Credentials file not found: {e}")
            raise
        except GoogleAuthError as e:
            logger.error(f"Google authentication error: {e}")
            raise
        except gspread.exceptions.APIError as e:
            logger.error(f"Google Sheets API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing Google Sheets client: {e}")
            raise
    
    def _ensure_headers(self):
        """Ensure the sheet has proper headers in the specified row."""
        try:
            # Check if headers exist in the specified row
            existing_headers = self.worksheet.row_values(self.header_row)
            
            # If sheet is empty or headers don't match, set them
            # Headers go in: A, B, C (Description merged across C-F), G, H, I, J, K
            # We need to place headers in the correct columns accounting for merged Description
            if not existing_headers or len(existing_headers) < len(self.HEADERS):
                # Create header row with empty columns for D, E, F (merged Description area)
                header_row_data = [
                    self.HEADERS[0],  # A - Task ID
                    self.HEADERS[1],  # B - Status
                    self.HEADERS[2],  # C - Description (merged across C-F)
                    "",  # D - Empty (part of merged Description)
                    "",  # E - Empty (part of merged Description)
                    "",  # F - Empty (part of merged Description)
                    self.HEADERS[3],  # G - Assigned to
                    self.HEADERS[4],  # H - Start Date
                    self.HEADERS[5],  # I - End Date
                    self.HEADERS[6],  # J - Measurable Outcome
                    self.HEADERS[7]   # K - Actual Outcome
                ]
                header_range = f'A{self.header_row}:K{self.header_row}'
                self.worksheet.update(header_range, [header_row_data])
                logger.info(f"Sheet headers initialized in row {self.header_row}")
        except Exception as e:
            logger.error(f"Error ensuring headers: {e}")
            raise
    
    def add_task(
        self,
        description: str,
        assigned_to: str,
        start_date: str,
        end_date: str,
        measurable_outcome: str
    ) -> int:
        """
        Add a new task to the Google Sheet.
        
        Args:
            description: Task description
            assigned_to: Username or Discord mention
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            measurable_outcome: Expected outcome
            
        Returns:
            Task number (auto-incremented)
            
        Raises:
            ValueError: If dates are invalid or end date is before start date
            Exception: If Google Sheets operation fails
        """
        try:
            # Validate dates
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD")
            
            # Validate end date is after start date
            if end_dt < start_dt:
                raise ValueError("End date must be after start date")
            
            # Get the next task number
            task_number = self._get_next_task_number()
            
            # Prepare the new row
            # Columns: A=Task ID, B=Status, C-F=Description (merged), G=Assigned to, H=Start Date, I=End Date, J=Measurable Outcome, K=Actual Outcome
            # Note: Description is in column C, but merged across C-F, so we need to account for empty columns D, E, F
            new_row = [
                task_number,  # A
                "",  # B - Status starts empty (can be set later)
                description,  # C - Description (merged across C-F)
                "",  # D - Empty (part of merged Description)
                "",  # E - Empty (part of merged Description)
                "",  # F - Empty (part of merged Description)
                assigned_to,  # G
                start_date,  # H
                end_date,  # I
                measurable_outcome,  # J
                ""  # K - Actual Outcome starts empty
            ]
            
            # Append the row to the sheet
            self.worksheet.append_row(new_row)
            
            # Find the row number we just inserted
            # After appending, we need to determine which row was created to merge cells
            all_values = self.worksheet.get_all_values()
            inserted_row = len(all_values)  # The row we just inserted (1-indexed)
            
            # Merge cells C-F for the Description column to match sheet formatting
            # The Description field is merged across columns C, D, E, F for better display
            merge_range = f'C{inserted_row}:F{inserted_row}'
            try:
                # Use Google Sheets API batch_update to merge cells
                # This requires the sheet ID (gid) and uses 0-indexed coordinates
                sheet_id = self.worksheet.id
                
                # Create the merge request following Google Sheets API format
                merge_request = {
                    "mergeCells": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": inserted_row - 1,  # 0-indexed (convert from 1-indexed)
                            "endRowIndex": inserted_row,        # End row (exclusive)
                            "startColumnIndex": 2,  # Column C (0-indexed: A=0, B=1, C=2)
                            "endColumnIndex": 6    # Column F+1 (0-indexed: C=2, D=3, E=4, F=5, end=6)
                        },
                        "mergeType": "MERGE_ALL"  # Merge all cells in the range
                    }
                }
                
                # Execute the batch update via Google Sheets API
                self.spreadsheet.batch_update({"requests": [merge_request]})
                logger.info(f"Merged Description cells {merge_range} for task #{task_number}")
            except Exception as e:
                # Log warning but continue - the data is still saved even if merge fails
                logger.warning(f"Failed to merge cells {merge_range}: {e}")
                # Note: The task data is still saved, only the formatting merge failed
            
            logger.info(f"Added task #{task_number}: {description}")
            return task_number
            
        except ValueError:
            raise
        except gspread.exceptions.APIError as e:
            logger.error(f"Google Sheets API error adding task: {e}")
            raise Exception(f"Failed to add task to Google Sheets: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error adding task: {e}")
            raise Exception(f"Failed to add task: {str(e)}")
    
    def _get_next_task_number(self) -> int:
        """
        Get the next task number by reading the last row.
        
        Returns:
            Next task number
        """
        try:
            # Get all values in the Task ID column (column A)
            number_column = self.worksheet.col_values(1)
            
            # Skip rows up to and including the header row
            # Data starts after header_row (e.g., if header is row 6, data starts at row 7)
            if len(number_column) <= self.header_row:
                return 1
            
            # Get all numbers (skip header row and any rows before it)
            numbers = []
            for i, val in enumerate(number_column, start=1):
                # Skip header row and rows before it
                if i <= self.header_row:
                    continue
                try:
                    if val.strip():  # Only process non-empty values
                        numbers.append(int(val))
                except (ValueError, AttributeError):
                    continue
            
            # Return next number
            if numbers:
                return max(numbers) + 1
            else:
                return 1
                
        except Exception as e:
            logger.error(f"Error getting next task number: {e}")
            # Default to 1 if we can't determine
            return 1
    
    def get_tasks(self, assigned_to: Optional[str] = None) -> List[Dict]:
        """
        Get all tasks, optionally filtered by assigned user.
        
        Args:
            assigned_to: Optional username to filter by
            
        Returns:
            List of task dictionaries
        """
        try:
            # Get all rows
            all_rows = self.worksheet.get_all_values()
            # Skip rows up to and including the header row
            # Data starts after header_row (e.g., if header is row 6, data starts at row 7)
            # header_row is 1-indexed (row 6), but list is 0-indexed (index 5), so data starts at index 6
            data_rows = all_rows[self.header_row:]  # Skip header row and rows before it (header_row is 1-indexed)
            
            tasks = []
            for row in data_rows:
                # Skip empty rows
                if not row or not row[0]:
                    continue
                
                # Extract task data
                # Columns: A=Task ID (0), B=Status (1), C=Description (2, merged across C-F), D=empty (3), E=empty (4), F=empty (5),
                #          G=Assigned to (6), H=Start Date (7), I=End Date (8), J=Measurable Outcome (9), K=Actual Outcome (10)
                task = {
                    "number": row[0] if len(row) > 0 else "",
                    "task_id": row[0] if len(row) > 0 else "",
                    "status": row[1] if len(row) > 1 else "",
                    "description": row[2] if len(row) > 2 else "",  # Column C (Description is merged across C-F)
                    "assigned_to": row[6] if len(row) > 6 else "",  # Column G
                    "start_date": row[7] if len(row) > 7 else "",  # Column H
                    "end_date": row[8] if len(row) > 8 else "",  # Column I
                    "measurable_outcome": row[9] if len(row) > 9 else "",  # Column J
                    "actual_outcome": row[10] if len(row) > 10 else ""  # Column K
                }
                
                # Filter by assigned_to if specified
                if assigned_to:
                    # Check if assigned_to matches (case-insensitive, partial match)
                    assigned_lower = task["assigned_to"].lower()
                    filter_lower = assigned_to.lower()
                    
                    # Check exact match or if username contains the filter
                    if (assigned_lower == filter_lower or 
                        filter_lower in assigned_lower or
                        assigned_lower in filter_lower):
                        tasks.append(task)
                else:
                    tasks.append(task)
            
            # Reverse the list so most recent tasks appear first
            # This provides a better UX when viewing tasks (newest at top)
            tasks.reverse()
            
            logger.info(f"Retrieved {len(tasks)} task(s)" + (f" for {assigned_to}" if assigned_to else ""))
            return tasks
            
        except gspread.exceptions.APIError as e:
            logger.error(f"Google Sheets API error getting tasks: {e}")
            raise Exception(f"Failed to retrieve tasks from Google Sheets: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting tasks: {e}")
            raise Exception(f"Failed to retrieve tasks: {str(e)}")
    
    def get_user_tasks(self, user_identifier: str) -> List[Dict]:
        """
        Get tasks assigned to a specific user.
        
        Args:
            user_identifier: Username, Discord mention, or partial match
            
        Returns:
            List of task dictionaries for the user
        """
        return self.get_tasks(assigned_to=user_identifier)
    
    def update_task_outcome(self, task_number: int, actual_outcome: str) -> bool:
        """
        Update the Actual Outcome column for a task.
        
        Args:
            task_number: The task number to update
            actual_outcome: The actual outcome text
            
        Returns:
            True if successful, False if task not found
            
        Raises:
            Exception: If Google Sheets operation fails
        """
        try:
            # Find the row with this task number
            number_column = self.worksheet.col_values(1)
            
            # Find the row index (1-indexed, skip header row and rows before it)
            row_index = None
            for i, val in enumerate(number_column, start=1):
                # Skip header row and rows before it
                if i <= self.header_row:
                    continue
                try:
                    if val and int(val) == task_number:
                        row_index = i
                        break
                except (ValueError, AttributeError):
                    continue
            
            if row_index is None:
                logger.warning(f"Task #{task_number} not found")
                return False
            
            # Update the Actual Outcome column (column K)
            # Column structure: A=Task ID, B=Status, C-F=Description (merged), G=Assigned to,
            #                  H=Start Date, I=End Date, J=Measurable Outcome, K=Actual Outcome
            cell = f"K{row_index}"
            # The gspread update method expects a list of lists (values)
            # Format: [[value]] for a single cell update
            self.worksheet.update(cell, [[actual_outcome]])
            
            logger.info(f"Updated outcome for task #{task_number}")
            return True
            
        except gspread.exceptions.APIError as e:
            logger.error(f"Google Sheets API error updating task: {e}")
            raise Exception(f"Failed to update task in Google Sheets: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error updating task: {e}")
            raise Exception(f"Failed to update task: {str(e)}")

