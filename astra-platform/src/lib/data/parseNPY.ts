import * as fs from 'fs';

export function parseNPY(filepath: string): number[] {
  const buffer = fs.readFileSync(filepath);
  
  // Magic: \x93NUMPY
  if (buffer[0] !== 0x93 || buffer.slice(1, 6).toString() !== 'NUMPY') {
    throw new Error('Not a valid .npy file');
  }
  
  const majorVersion = buffer[6];
  // const minorVersion = buffer[7];
  
  let headerLen: number;
  let headerStart: number;
  
  if (majorVersion === 1) {
    headerLen = buffer.readUInt16LE(8);
    headerStart = 10;
  } else {
    // version 2.0+
    headerLen = buffer.readUInt32LE(8);
    headerStart = 12;
  }
  
  const headerStr = buffer.slice(headerStart, headerStart + headerLen).toString();
  
  // Parse dtype from header
  const dtypeMatch = headerStr.match(/'descr':\s*'([^']+)'/);
  const dtype = dtypeMatch ? dtypeMatch[1] : '<f8';
  
  const dataStart = headerStart + headerLen;
  const dataBuffer = buffer.slice(dataStart);
  
  // Handle float64 (f8) and float32 (f4)
  const bytesPerElement = dtype.includes('f8') || dtype.includes('f64') ? 8 : 4;
  const n = dataBuffer.length / bytesPerElement;
  const result: number[] = new Array(n);
  
  for (let i = 0; i < n; i++) {
    if (bytesPerElement === 8) {
      result[i] = dataBuffer.readDoubleBE ? 
        (dtype.startsWith('>') ? dataBuffer.readDoubleBE(i * 8) : dataBuffer.readDoubleLE(i * 8)) :
        dataBuffer.readDoubleLE(i * 8);
    } else {
      result[i] = dtype.startsWith('>') ? dataBuffer.readFloatBE(i * 4) : dataBuffer.readFloatLE(i * 4);
    }
  }
  
  return result;
}
