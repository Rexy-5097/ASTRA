import { NextResponse } from 'next/server';
import { SYSTEM_METRICS, CHECKPOINT_REGISTRY } from '@/lib/data/constants';

export async function GET() {
  return NextResponse.json({
    ...SYSTEM_METRICS,
    checkpoints: CHECKPOINT_REGISTRY,
  });
}
