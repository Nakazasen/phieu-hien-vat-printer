"""
Backup and Safe Staging Manager for PPTX files.
Provides SHA-256 verification, local backup staging, and safe network deployment.
"""

import os
import shutil
import hashlib
import datetime
from typing import Dict, Optional, Tuple


class BackupManager:
    """
    Manages local backups, SHA-256 checksums, local staging copies,
    and safe atomic overwrites to target network UNC shares.
    """

    def __init__(self, base_backup_dir: Optional[str] = None, staging_dir: Optional[str] = None):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.backup_dir = base_backup_dir or os.path.join(
            project_root, "backups", "pptx_inputs", timestamp
        )
        self.staging_dir = staging_dir or os.path.join(project_root, "output")
        
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.staging_dir, exist_ok=True)
        
        self.manifest: Dict[str, Dict[str, str]] = {}

    @staticmethod
    def calculate_sha256(file_path: str) -> str:
        """Computes SHA-256 checksum of a file in 64KB chunks."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found for hash calculation: {file_path}")
        
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    def backup_and_stage(self, source_path: str) -> Tuple[str, str, str]:
        """
        Creates a verified backup copy and prepares a local staging file.
        
        Returns:
            Tuple of (staged_working_path, backup_path, original_sha256)
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file does not exist: {source_path}")

        file_name = os.path.basename(source_path)
        original_hash = self.calculate_sha256(source_path)

        # 1. Create backup copy
        backup_path = os.path.join(self.backup_dir, file_name)
        shutil.copy2(source_path, backup_path)
        backup_hash = self.calculate_sha256(backup_path)

        if original_hash != backup_hash:
            raise IOError(
                f"Backup SHA-256 mismatch for {file_name}: "
                f"Original={original_hash} vs Backup={backup_hash}"
            )

        # 2. Create local staging working copy
        staged_path = os.path.join(self.staging_dir, file_name)
        shutil.copy2(source_path, staged_path)
        staged_hash = self.calculate_sha256(staged_path)

        if original_hash != staged_hash:
            raise IOError(
                f"Staged copy SHA-256 mismatch for {file_name}: "
                f"Original={original_hash} vs Staged={staged_hash}"
            )

        self.manifest[file_name] = {
            "source_path": source_path,
            "backup_path": backup_path,
            "staged_path": staged_path,
            "original_sha256": original_hash,
            "backup_sha256": backup_hash,
            "timestamp": datetime.datetime.now().isoformat(),
        }

        return staged_path, backup_path, original_hash

    def deploy_to_network(self, staged_path: str, target_unc_path: str) -> str:
        """
        Safely deploys the processed staging file to the target network UNC path
        using atomic safe write-back (.tmp -> SHA-256 verify -> atomic replace).
        
        Returns:
            deployed_sha256
        """
        if not os.path.exists(staged_path):
            raise FileNotFoundError(f"Staged file not found for deployment: {staged_path}")

        staged_hash = self.calculate_sha256(staged_path)
        target_dir = os.path.dirname(target_unc_path)
        
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        tmp_unc_path = target_unc_path + ".tmp"
        
        # Clean up any leftover temporary file first if it exists
        if os.path.exists(tmp_unc_path):
            try:
                os.remove(tmp_unc_path)
            except OSError:
                pass

        try:
            # 1. Write first to target_unc_path + ".tmp"
            shutil.copy2(staged_path, tmp_unc_path)

            # 2. Verify SHA-256 of temporary file
            tmp_hash = self.calculate_sha256(tmp_unc_path)
            if staged_hash != tmp_hash:
                raise IOError(
                    f"Network temporary file SHA-256 mismatch for {tmp_unc_path}: "
                    f"Staged={staged_hash} vs Temp={tmp_hash}"
                )

            # 3. Perform atomic replace / safe rename
            try:
                os.replace(tmp_unc_path, target_unc_path)
            except OSError:
                if os.path.exists(target_unc_path):
                    os.remove(target_unc_path)
                os.rename(tmp_unc_path, target_unc_path)

        except Exception as e:
            if os.path.exists(tmp_unc_path):
                try:
                    os.remove(tmp_unc_path)
                except OSError:
                    pass
            raise e

        # 4. Final verification
        target_hash = self.calculate_sha256(target_unc_path)
        if staged_hash != target_hash:
            raise IOError(
                f"Network deployment SHA-256 mismatch for {target_unc_path}: "
                f"Staged={staged_hash} vs Target={target_hash}"
            )

        file_name = os.path.basename(target_unc_path)
        if file_name in self.manifest:
            self.manifest[file_name]["deployed_sha256"] = target_hash
            self.manifest[file_name]["deployed_time"] = datetime.datetime.now().isoformat()

        return target_hash
