import subprocess
import os
import fcntl
from typing import List, Optional

class GMNInterface:
    def __init__(self, binary_path: str = "gmn"):
        self.binary_path = binary_path

    def query(self, prompt: str, system_file: str, context_files: List[str], extra_files: Optional[List[str]] = None) -> str:
        """
        gmn CLI を呼び出して Gemini API から応答を取得する
        """
        args = [self.binary_path, "-f", system_file]
        for f in context_files:
            if os.path.exists(f):
                args.extend(["-f", f])
        
        if extra_files:
            for f in extra_files:
                if os.path.exists(f):
                    args.extend(["-f", f])
        
        try:
            result = subprocess.run(
                args,
                input=prompt,
                text=True,
                capture_output=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error calling gmn: {e.stderr}")
            raise e

class ContextManager:
    def __init__(self, base_data_path: str = "data"):
        self.base_data_path = base_data_path

    def _get_path(self, guild_id: int, channel_id: int, filename: str) -> str:
        path = os.path.join(self.base_data_path, str(guild_id), str(channel_id))
        os.makedirs(path, exist_ok=True)
        return os.path.join(path, filename)

    def append_message(self, guild_id: int, channel_id: int, timestamp: str, user: str, content: str):
        """
        当日分のログ(current.txt)にメッセージを追記する
        """
        file_path = self._get_path(guild_id, channel_id, "current.txt")
        line = f"[{timestamp}] {user}: {content}\n"
        
        with open(file_path, "a") as f:
            # 排他ロックを取得
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(line)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def get_context_files(self, guild_id: int, channel_id: int) -> List[str]:
        """
        gmn に渡すコンテキストファイルのパス一覧を返す
        """
        files = ["archive.txt", "current.txt"]
        # system.txt はグローバルかフォルダ内か検討が必要だが、一旦フォルダ内
        return [self._get_path(guild_id, channel_id, f) for f in files]

    def set_system_prompt(self, guild_id: int, channel_id: int, prompt: str):
        file_path = self._get_path(guild_id, channel_id, "system.txt")
        with open(file_path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(prompt)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
