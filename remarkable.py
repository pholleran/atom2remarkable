"""
reMarkable Cloud integration using rmapi
"""
import subprocess
import logging
from pathlib import Path
from typing import List, Optional
from config import Config

class RemarkableUploader:
    """Handles uploading PDFs to reMarkable Cloud using rmapi"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rmapi_path = Config.RMAPI_PATH
        self.folder_name = Config.REMARKABLE_FOLDER
        
    def check_rmapi_available(self) -> bool:
        """Check if rmapi is available and configured"""
        try:
            result = subprocess.run(
                [self.rmapi_path, 'version'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                self.logger.info(f"rmapi available: {result.stdout.strip()}")
                return True
            else:
                self.logger.error(f"rmapi error: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            self.logger.error("rmapi version check timed out")
            return False
        except FileNotFoundError:
            self.logger.error(f"rmapi not found at path: {self.rmapi_path}")
            return False
        except Exception as e:
            self.logger.error(f"Error checking rmapi availability: {e}")
            return False
    
    def ensure_folder_exists(self) -> bool:
        """Ensure the target folder exists in reMarkable Cloud"""
        try:
            # Check if folder already exists
            result = subprocess.run(
                [self.rmapi_path, 'find', self.folder_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                self.logger.info(f"Folder '{self.folder_name}' already exists")
                return True
            
            # Create folder if it doesn't exist
            self.logger.info(f"Creating folder '{self.folder_name}' in reMarkable Cloud")
            result = subprocess.run(
                [self.rmapi_path, 'mkdir', self.folder_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully created folder '{self.folder_name}'")
                return True
            else:
                # Check if it failed because folder already exists
                if "already exists" in result.stderr.lower():
                    self.logger.info(f"Folder '{self.folder_name}' already exists")
                    return True
                self.logger.error(f"Failed to create folder: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Folder creation timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error ensuring folder exists: {e}")
            return False
    
    def ensure_subfolder_exists(self, subfolder_path: str) -> bool:
        """Ensure a subfolder exists in reMarkable Cloud"""
        try:
            # Check if subfolder already exists
            result = subprocess.run(
                [self.rmapi_path, 'find', subfolder_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                self.logger.info(f"Subfolder '{subfolder_path}' already exists")
                return True
            
            # Create subfolder if it doesn't exist
            self.logger.info(f"Creating subfolder '{subfolder_path}' in reMarkable Cloud")
            result = subprocess.run(
                [self.rmapi_path, 'mkdir', subfolder_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully created subfolder '{subfolder_path}'")
                return True
            else:
                # Check if it failed because folder already exists
                if "already exists" in result.stderr.lower():
                    self.logger.info(f"Subfolder '{subfolder_path}' already exists")
                    return True
                self.logger.error(f"Failed to create subfolder: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Subfolder creation timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error ensuring subfolder exists: {e}")
            return False
    
    def file_exists_in_remarkable(self, file_path: str) -> bool:
        """Check if a file already exists in reMarkable Cloud"""
        try:
            # Use rmapi find to check if file exists
            result = subprocess.run(
                [self.rmapi_path, 'find', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # If find returns 0 and has output, file exists
            if result.returncode == 0 and result.stdout.strip():
                return True
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking if file exists in reMarkable: {e}")
            return False  # If we can't check, assume it doesn't exist and try upload
    
    def get_remarkable_file_path(self, pdf_path: Path, feed_subfolder: Optional[str] = None) -> str:
        """Get the full path where a file would be stored in reMarkable Cloud"""
        # Remove .pdf extension for reMarkable file name
        file_name = pdf_path.stem
        
        if feed_subfolder:
            return f"{self.folder_name}/{feed_subfolder}/{file_name}"
        else:
            return f"{self.folder_name}/{file_name}"
    
    def upload_pdf(self, pdf_path: Path, feed_subfolder: Optional[str] = None) -> bool:
        """Upload a single PDF to reMarkable Cloud"""
        try:
            # Check if file already exists in reMarkable Cloud
            remarkable_file_path = self.get_remarkable_file_path(pdf_path, feed_subfolder)
            if self.file_exists_in_remarkable(remarkable_file_path):
                self.logger.info(f"File already exists in reMarkable Cloud, skipping: {pdf_path.name}")
                return True  # Consider this a successful "upload"
            
            # Determine target folder path
            if feed_subfolder:
                target_folder = f"{self.folder_name}/{feed_subfolder}"
                
                # Ensure main folder exists first
                if not self.ensure_folder_exists():
                    return False
                
                # Then ensure subfolder exists
                if not self.ensure_subfolder_exists(target_folder):
                    return False
            else:
                target_folder = self.folder_name
                if not self.ensure_folder_exists():
                    return False
            
            self.logger.info(f"Uploading {pdf_path.name} to reMarkable folder: {target_folder}")
            
            # Upload the PDF
            result = subprocess.run(
                [self.rmapi_path, 'put', str(pdf_path), target_folder],
                capture_output=True,
                text=True,
                timeout=120  # Longer timeout for uploads
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully uploaded {pdf_path.name}")
                return True
            else:
                self.logger.error(f"Failed to upload {pdf_path.name}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Upload timed out for {pdf_path.name}")
            return False
        except Exception as e:
            self.logger.error(f"Error uploading {pdf_path.name}: {e}")
            return False
    
    def upload_pdfs(self, pdf_files: List[Path]) -> dict:
        """Upload multiple PDFs to reMarkable Cloud"""
        if not self.check_rmapi_available():
            self.logger.error("rmapi not available, cannot upload to reMarkable")
            return {'uploaded': 0, 'failed': 0, 'skipped': len(pdf_files)}
        
        if not self.ensure_folder_exists():
            self.logger.error("Failed to ensure folder exists, skipping uploads")
            return {'uploaded': 0, 'failed': 0, 'skipped': len(pdf_files)}
        
        uploaded = 0
        failed = 0
        skipped = 0
        
        for pdf_path in pdf_files:
            try:
                # Extract feed subfolder from path if it exists
                # e.g., output/Simon_Willisons_Weblog/file.pdf -> Simon_Willisons_Weblog
                parts = pdf_path.parts
                feed_subfolder = None
                if len(parts) >= 3 and parts[-3] == 'output':
                    feed_subfolder = parts[-2]
                
                # Check if file already exists in reMarkable Cloud before uploading
                remarkable_file_path = self.get_remarkable_file_path(pdf_path, feed_subfolder)
                if self.file_exists_in_remarkable(remarkable_file_path):
                    self.logger.info(f"File already exists in reMarkable Cloud, skipping: {pdf_path.name}")
                    skipped += 1
                    continue
                
                if self.upload_pdf(pdf_path, feed_subfolder):
                    uploaded += 1
                else:
                    failed += 1
                    
            except Exception as e:
                self.logger.error(f"Unexpected error processing {pdf_path.name}: {e}")
                failed += 1
        
        self.logger.info(f"reMarkable upload summary: {uploaded} uploaded, {skipped} skipped, {failed} failed")
        return {'uploaded': uploaded, 'failed': failed, 'skipped': skipped}
    
    def list_remarkable_files(self) -> Optional[str]:
        """List files in the reMarkable folder for debugging"""
        if not self.check_rmapi_available():
            return None
            
        try:
            result = subprocess.run(
                [self.rmapi_path, 'ls', self.folder_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                self.logger.error(f"Failed to list reMarkable files: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error listing reMarkable files: {e}")
            return None
