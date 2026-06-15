from supabase import create_client, Client
from typing import List, Dict, Any, Optional
import os
from datetime import datetime, timezone

class SupabaseManager:
    """Quản lý kết nối và các thao tác với Supabase"""

    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)

    async def create_game_session(self, game_id: str, game_name: str, players: List[str],
                                  mode: str) -> Dict[str, Any]:
        """Tạo một phiên chơi mới"""
        data = {
            'game_id': game_id,
            'game_name': game_name,
            'players': players,
            'mode': mode,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'status': 'in_progress'
        }

        response = self.client.table('game_sessions').insert(data).execute()
        return response.data[0] if response.data else None

    async def save_game_state(self, game_id: str, game_state: Dict[str, Any]) -> None:
        """Lưu trạng thái trò chơi"""
        data = {
            'game_id': game_id,
            'state': game_state,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }

        self.client.table('game_states').upsert(data).execute()

    async def save_move(self, game_id: str, player_name: str, move_data: Dict[str, Any]) -> None:
        """Lưu nước đi"""
        data = {
            'game_id': game_id,
            'player_name': player_name,
            'move_data': move_data,
            'created_at': datetime.now(timezone.utc).isoformat()
        }

        self.client.table('moves').insert(data).execute()

    async def finish_game(self, game_id: str, winner: str, final_state: Dict[str, Any]) -> None:
        """Hoàn thành trò chơi"""
        data = {
            'status': 'finished',
            'winner': winner,
            'final_state': final_state,
            'finished_at': datetime.now(timezone.utc).isoformat()
        }

        self.client.table('game_sessions').update(data).eq('game_id', game_id).execute()

    async def get_player_stats(self, player_name: str) -> Dict[str, Any]:
        """Lấy thống kê người chơi"""
        response = self.client.table('game_sessions').select(
            'game_name, winner'
        ).eq('players', f'%{player_name}%').execute()

        games = response.data or []
        total_games = len(games)
        wins = sum(1 for g in games if g['winner'] == player_name)

        return {
            'player_name': player_name,
            'total_games': total_games,
            'wins': wins,
            'win_rate': (wins / total_games * 100) if total_games > 0 else 0
        }

    async def get_leaderboard(self, game_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lấy bảng xếp hạng"""
        query = self.client.table('game_sessions').select('winner, game_name')

        if game_name:
            query = query.eq('game_name', game_name)

        response = query.execute()
        games = response.data or []

        # Tính toán thống kê
        stats = {}
        for game in games:
            winner = game.get('winner')
            if winner:
                if winner not in stats:
                    stats[winner] = 0
                stats[winner] += 1

        # Sắp xếp
        leaderboard = sorted(stats.items(), key=lambda x: x[1], reverse=True)
        return [{'rank': i + 1, 'player': p[0], 'wins': p[1]} for i, p in enumerate(leaderboard)]
