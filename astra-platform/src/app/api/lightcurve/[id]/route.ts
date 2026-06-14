import { NextRequest, NextResponse } from 'next/server';
import * as path from 'path';
import { parseNPY } from '@/lib/data/parseNPY';

export const dynamic = 'force-dynamic';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const ticId = id.replace('TIC_', '');
  
  const dataRoot = path.join(process.cwd(), 'data', 'processed', `TIC_${ticId}`);
  
  try {
    const flux1000 = parseNPY(path.join(dataRoot, 'flux_1000.npy'));
    const flux200 = parseNPY(path.join(dataRoot, 'flux_200.npy'));
    const foldedFlux1000 = parseNPY(path.join(dataRoot, 'folded_flux_1000.npy'));
    const foldedFlux200 = parseNPY(path.join(dataRoot, 'folded_flux_200.npy'));
    
    return NextResponse.json({
      tic_id: parseInt(ticId),
      flux_1000: flux1000,
      flux_200: flux200,
      folded_flux_1000: foldedFlux1000,
      folded_flux_200: foldedFlux200,
    });
  } catch (error) {
    return NextResponse.json({ error: `Light curve not found: ${error}` }, { status: 404 });
  }
}
