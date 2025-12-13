


export type Founder = {
  name: string;
  education: string | null;
  previous_ventures: string | null;
  professional_background: string | null;
  years_of_relevant_experience?: number;
  previous_ventures_outcome?: string;
};

export type CompanyOverview = {
  name: string;
  sector: string;
  founders: Founder[];
  technology?: string;
  technologies_used?: string;
  key_problems_solved?: string[];
  intellectual_property_details?: string;
};

export type MarketReport = {
  summary: string;
  title: string;
  source_name: string;
  source_url: string;
};

export type MarketValue = {
  value: string;
  cagr: string;
  source: string;
  projection?: string;
  name: string;
};

export type CompetitorDetail = {
  name: string;
  business_model: string;
  funding_rounds?: string;
  total_funding_raised: string;
  investors: string;
  revenue_streams: string;
  target_market: string;
  current_arr?: string;
  founding_year?: number;
  headquarters?: string;
  current_mrr?: string;
  gross_margin?: string;
  net_margin?: string;
  [key: string]: any;
};

export type MarketAnalysis = {
  industry_size_and_growth: {
    total_addressable_market: MarketValue;
    serviceable_obtainable_market?: MarketValue;
    serviceable_available_market?: MarketValue;
    commentary: string;
  };
  reports: MarketReport[];
  competitor_details: CompetitorDetail[];
  sub_segment_opportunities: string[];
};

export type BusinessModel = {
  revenue_streams: string;
  pricing: string;
  scalability: string;
  description: string;
  target_audience: string;
  percentage_contribution: string;
  additional_revenue_opportunities: string[];
  unit_economics: {
    lifetime_value_LTV?: string;
    customer_acquisition_cost_CAC?: string;
    LTV_CAC_Ratio?: string;
    lifetime_value_LTV_calculation?: string;
    customer_acquisition_cost_CAC_calculation?: string;
  };
  customer_acquisition_channels?: string;
  sales_cycle_details?: string;
};

export type FinancialProjection = {
  revenue: string;
  year: string;
  comment?: string;
};

export type Financials = {
  funding_history: string;
  projections: FinancialProjection[];
  valuation_rationale: string;
  arr_mrr: {
    current_booked_arr: string;
    current_mrr: string;
  };
  burn_and_runway: {
    funding_ask: string;
    stated_runway: string;
    implied_net_burn: string;
    gross_margin?: string;
    cm1?: string;
    cm2?: string;
    cm3?: string;
  };
};

export type Claim = {
  result: string;
  simulated_probability: string | number;
  simulation_assumptions: {
    average_contract_value?: string;
    base_revenue?: string;
    engagement_conversion_rate?: string;
    pilot_conversion_rate?: string;
    runs?: string;
    time_horizon_months?: number;
    initial_customers?: number;
    acv_distribution?: string;
    assumptions?: string;
  };
  analysis_method: string;
  claim: string;
  input_dataset_length?: number;
};

export type ClaimsAnalysis = Claim[];

export type RiskMetrics = {
  narrative_justification: string;
  composite_risk_score: number;
  score_interpretation: string;
};

export type RiskAndMitigation = {
  risk: string;
  description: string;
  likelihood: string;
  impact: string;
  mitigation: string;
};

export type Conclusion = {
  overall_attractiveness: string;
  product_summary?: string;
  financial_analysis?: string;
  investment_thesis?: string;
  risk_summary?: string;
};

export type InterviewInsights = {
  ltv_cac_reconciliation?: string;
  contribution_margins?: string;
  sam_details?: string;
  founder_experience_sumalata?: string;
  monthly_burn_reconciliation?: string;
  founder_experience_karthik?: string;
  funding_history_details?: string;
  arr_mrr_reconciliation?: string;
}

// Credit Analysis Types for 4-Gate Framework
export type GateCheck = {
  name: string;
  status: string;
  result: string;
  details: string;
  flags?: string[];
};

export type Gate = {
  gate_number: number;
  gate_name: string;
  status: string;
  checks: GateCheck[];
};

export type SummaryTableEntry = {
  parameter: string;
  result: string;
  status: string;
};

export type CreditAnalysis = {
  gates: Gate[];
  loan_amount_requested: string;
  max_permissible_limit: string;
  dscr: string;
  current_ratio: string;
  tol_tnw_ratio: string;
  runway_months: string;
  recommendation: string;
  sanction_amount: string;
  conditions: string[];
  rejection_reasons: string[];
  cgtmse_eligible: boolean;
  summary_table: SummaryTableEntry[];
  final_verdict: string;
};

export type MemoV1 = {
  claims_analysis: ClaimsAnalysis;
  market_analysis: MarketAnalysis;
  financials: Financials;
  company_overview: CompanyOverview;
  conclusion: Conclusion;
  business_model: BusinessModel[];
  risk_metrics: RiskMetrics;
  risks_and_mitigation: RiskAndMitigation[];
  interview_summary: string;
  interview_insights: InterviewInsights;
  credit_analysis?: CreditAnalysis;
  _weightage_used: Record<string, number>;
};

export type Memo = {
  docx_url: string;
  draft_v1: MemoV1;
  generated_at: string;
  last_updated: string;
  includes_interview_data: boolean;
};

export type Metadata = {
  created_at: string;
  sector: string;
  deal_id: string;
  company_name: string;
  founder_names: string[];
  error: string | null;
  status: string;
  processed_at: string;
  processing_mode?: 'fast' | 'research';
  weightage: {
    claim_credibility: number;
    financial_health: number;
    market_opportunity: number;
    team_strength: number;
    traction: number;
  };
};

export type InterviewIssue = {
  status: string;
  question: string;
  category: string;
  field: string;
  importance: string;
};

export type Interview = {
  chat_history: any[];
  missing_fields: string[];
  founder_email: string;
  gathered_info: any;
  expires_at: string;
  issues: InterviewIssue[];
  completed_at: string | null;
  founder_name: string;
  status: string;
  created_at: string;
  started_at: string | null;
  token: string;
};

export type PublicData = {
  news: any[];
  founder_profile: any[];
  competitors: CompetitorDetail[];
  market_stats: any;
};

export type AnalysisData = {
  memo: Memo;
  raw_files: {
    pitch_deck_url: string;
    video_pitch_deck_url?: string;
    audio_pitch_deck_url?: string;
    text_pitch_deck_url?: string;
  };
  timestamp: string;
};

export type ChatMessage = {
  role: 'assistant' | 'user';
  message: string;
  timestamp: string;
};

export type ValidationResponse = {
  valid: boolean;
  deal_id: string;
  company_name: string;
  sector: string;
  founder_name: string;
  status: 'active' | 'completed' | 'expired';
  missing_fields_count: number;
  chat_history: ChatMessage[];
};
