-- PersonaPanel Supabase Schema

-- 1. test_sessions table
CREATE TABLE IF NOT EXISTS public.test_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    url TEXT NOT NULL,
    screenshot_url TEXT,
    overall_conversion_risk_score INTEGER,
    user_id UUID -- Optional, for authenticated users
);

-- 2. persona_results table
CREATE TABLE IF NOT EXISTS public.persona_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    test_session_id UUID REFERENCES public.test_sessions(id) ON DELETE CASCADE,
    persona_name TEXT NOT NULL,
    friction_points JSONB DEFAULT '[]'::jsonb,
    positive_signals JSONB DEFAULT '[]'::jsonb,
    would_convert BOOLEAN NOT NULL DEFAULT false,
    gut_reaction TEXT
);

-- 3. synthesis_results table
CREATE TABLE IF NOT EXISTS public.synthesis_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    test_session_id UUID REFERENCES public.test_sessions(id) ON DELETE CASCADE,
    top_priority_issues JSONB DEFAULT '[]'::jsonb,
    persona_specific_issues JSONB DEFAULT '[]'::jsonb,
    overall_conversion_risk_score INTEGER,
    summary TEXT
);
