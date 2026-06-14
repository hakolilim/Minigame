-- Create tables for Minigame Bot

-- Game Sessions Table
CREATE TABLE IF NOT EXISTS game_sessions (
    id BIGSERIAL PRIMARY KEY,
    game_id VARCHAR(8) UNIQUE NOT NULL,
    game_name VARCHAR(100) NOT NULL,
    players TEXT[] NOT NULL,
    mode VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'in_progress',
    winner VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    final_state JSONB
);

-- Game States Table
CREATE TABLE IF NOT EXISTS game_states (
    id BIGSERIAL PRIMARY KEY,
    game_id VARCHAR(8) UNIQUE NOT NULL REFERENCES game_sessions(game_id) ON DELETE CASCADE,
    state JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Moves Table (lịch sử nước đi)
CREATE TABLE IF NOT EXISTS moves (
    id BIGSERIAL PRIMARY KEY,
    game_id VARCHAR(8) NOT NULL REFERENCES game_sessions(game_id) ON DELETE CASCADE,
    player_name VARCHAR(100) NOT NULL,
    move_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_game_sessions_game_id ON game_sessions(game_id);
CREATE INDEX idx_game_sessions_winner ON game_sessions(winner);
CREATE INDEX idx_game_states_game_id ON game_states(game_id);
CREATE INDEX idx_moves_game_id ON moves(game_id);
CREATE INDEX idx_moves_player ON moves(player_name);

-- Set up Row Level Security (RLS) - mở công khai để dễ test
ALTER TABLE game_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE game_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE moves ENABLE ROW LEVEL SECURITY;

-- Create policies để cho phép anonymous access (vì Discord bot không có auth)
CREATE POLICY "Allow public read on game_sessions" ON game_sessions
    FOR SELECT USING (true);

CREATE POLICY "Allow public insert on game_sessions" ON game_sessions
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow public update on game_sessions" ON game_sessions
    FOR UPDATE USING (true) WITH CHECK (true);

CREATE POLICY "Allow public read on game_states" ON game_states
    FOR SELECT USING (true);

CREATE POLICY "Allow public insert on game_states" ON game_states
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow public update on game_states" ON game_states
    FOR UPDATE USING (true) WITH CHECK (true);

CREATE POLICY "Allow public read on moves" ON moves
    FOR SELECT USING (true);

CREATE POLICY "Allow public insert on moves" ON moves
    FOR INSERT WITH CHECK (true);
