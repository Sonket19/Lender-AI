
import type { MarketAnalysis as MarketAnalysisType, CompetitorDetail, PublicData } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, Scale, Newspaper, Target, Globe } from 'lucide-react';
import Link from 'next/link';

export default function MarketAnalysis({ data, publicData }: { data: MarketAnalysisType, publicData: PublicData }) {
  const competitors = data?.competitor_details || publicData?.competitors || [];
  const industryData = data?.industry_size_and_growth;
  const tam = industryData?.total_addressable_market;
  const som = industryData?.serviceable_obtainable_market;

  return (
    <div className="space-y-8">
      {industryData && (
        <Card>
          <CardHeader>
            <CardTitle className="font-headline text-2xl flex items-center gap-3"><TrendingUp className="w-7 h-7 text-primary" />Industry Size & Growth</CardTitle>
            {industryData.commentary && <CardDescription>{industryData.commentary}</CardDescription>}
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {tam && (
              <div className="space-y-2 p-4 bg-secondary/50 rounded-lg">
                <h4 className="font-semibold text-lg">{tam.name || 'Total Addressable Market'} (TAM)</h4>
                <p className="text-4xl font-bold font-headline text-primary">{tam.value || 'N/A'}</p>
                {tam.cagr && <Badge variant="secondary">CAGR: {tam.cagr}</Badge>}
              </div>
            )}
            {som && (
              <div className="space-y-2 p-4 bg-secondary/50 rounded-lg">
                <h4 className="font-semibold text-lg">{som.name || 'Serviceable Obtainable Market'} (SOM)</h4>
                <p className="text-4xl font-bold font-headline text-primary">{som.value || 'N/A'}</p>
                <div className="flex flex-wrap gap-2 items-center">
                  {som.cagr && <Badge variant="secondary">CAGR: {som.cagr}</Badge>}
                  {som.projection && (
                    <Badge variant="outline">Projection: {som.projection}</Badge>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {data?.sub_segment_opportunities && data.sub_segment_opportunities.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="font-headline text-2xl flex items-center gap-3"><Target className="w-7 h-7 text-primary" />Sub-segment Opportunities</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc list-inside text-muted-foreground">
              {data.sub_segment_opportunities.map((opp, i) => (
                <li key={i}>{opp}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {competitors && competitors.length > 0 && (
        <div>
          <h2 className="font-headline text-2xl mb-4 flex items-center gap-3"><Scale className="w-7 h-7 text-primary" />Competitor Details</h2>
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Competitor</TableHead>
                  <TableHead>Founded</TableHead>
                  <TableHead>Headquarters</TableHead>
                  <TableHead>Business Model</TableHead>
                  <TableHead>Funding Rounds</TableHead>
                  <TableHead>Total Funding</TableHead>
                  <TableHead>Investors</TableHead>
                  <TableHead>Target Market</TableHead>
                  <TableHead>Revenue Streams</TableHead>
                  <TableHead>Current ARR</TableHead>
                  <TableHead>Current MRR</TableHead>
                  <TableHead>Gross Margin</TableHead>
                  <TableHead>Net Margin</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {competitors.map((competitor) => (
                  <TableRow key={competitor.name}>
                    <TableCell className="font-medium">{competitor.name}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{competitor.founding_year || 'N/A'}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{competitor.headquarters || 'N/A'}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{competitor.business_model || 'N/A'}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{competitor.funding_rounds || 'N/A'}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{competitor.total_funding_raised || 'N/A'}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {Array.isArray(competitor.investors) ? competitor.investors.join(', ') : (competitor.investors || 'N/A')}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{competitor.target_market || 'N/A'}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{competitor.revenue_streams || 'N/A'}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{competitor.current_arr || 'N/A'}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{competitor.current_mrr || 'N/A'}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{competitor.gross_margin || 'N/A'}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{competitor.net_margin || 'N/A'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </div>
      )}

      {data?.reports && data.reports.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="font-headline text-2xl flex items-center gap-3"><Newspaper className="w-7 h-7 text-primary" />Market Reports</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {data.reports.map((report, i) => (
              <div key={i} className="p-4 border rounded-lg">
                <h3 className="font-semibold">{report.title}</h3>
                <p className="text-sm text-muted-foreground mt-1">{report.summary}</p>
                <div className="flex items-center justify-between mt-3">
                  <Badge variant="secondary">{report.source_name || 'Unknown Source'}</Badge>
                  {report.source_url ? (
                    <Link href={report.source_url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary hover:underline flex items-center gap-1">
                      <Globe className="w-3 h-3" />
                      Visit Source
                    </Link>
                  ) : (
                    <span className="text-sm text-muted-foreground flex items-center gap-1 opacity-50 cursor-not-allowed">
                      <Globe className="w-3 h-3" />
                      Source Link Unavailable
                    </span>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

    </div>
  );
}
