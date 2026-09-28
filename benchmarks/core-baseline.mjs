import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require=createRequire(import.meta.url);
const core=require("../core/timeline-core.js");
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const OUTPUT=path.join(ROOT,"artifacts","core-performance-baseline.json");
const COUNTS=[10,50,200,500,1000];
const ITERATIONS=20;

function layer(id,index,inFrame,outFrame){
  return {id,index,inFrame,outFrame};
}

function sequential(count){
  const layers=[];
  for(let i=0;i<count;i+=1){
    layers.push(layer(i+1,i+1,i*10,(i+1)*10));
  }
  return layers;
}

function fullOverlap(count){
  const layers=[];
  for(let i=0;i<count;i+=1){
    layers.push(layer(i+1,i+1,0,1000));
  }
  return layers;
}

function mixed(count){
  let seed=0x13579bdf;
  function random(){
    seed=(Math.imul(seed,1664525)+1013904223)>>>0;
    return seed/0x100000000;
  }

  const layers=[];
  for(let i=0;i<count;i+=1){
    const start=Math.floor(random()*2000)-500;
    const duration=1+Math.floor(random()*240);
    layers.push(layer(i+1,i+1,start,start+duration));
  }
  return layers;
}

function percentile(sorted,p){
  if(sorted.length===0)return 0;
  const index=Math.min(sorted.length-1,Math.max(0,Math.ceil(sorted.length*p)-1));
  return sorted[index];
}

function timeScenario(name,count,layers){
  for(let i=0;i<3;i+=1){
    core.packLayers(layers);
  }

  const samples=[];
  let lastResult=null;

  for(let i=0;i<ITERATIONS;i+=1){
    const start=process.hrtime.bigint();
    lastResult=core.packLayers(layers);
    const elapsed=Number(process.hrtime.bigint()-start)/1e6;
    samples.push(elapsed);
  }

  const validation=core.validatePacking(lastResult);
  if(!validation.ok){
    throw new Error(name+" "+count+" failed packing invariant: "+validation.error);
  }

  samples.sort((a,b)=>a-b);
  const sum=samples.reduce((acc,value)=>acc+value,0);

  return {
    scenario:name,
    layers:count,
    iterations:ITERATIONS,
    trackCount:lastResult.trackCount,
    minMs:samples[0],
    medianMs:percentile(samples,0.5),
    p95Ms:percentile(samples,0.95),
    maxMs:samples[samples.length-1],
    meanMs:sum/samples.length
  };
}

const scenarios=[
  ["sequential",sequential],
  ["full-overlap",fullOverlap],
  ["mixed",mixed]
];

const results=[];
for(const count of COUNTS){
  for(const [name,factory] of scenarios){
    results.push(timeScenario(name,count,factory(count)));
  }
}

const report={
  schemaVersion:1,
  runtime:{
    node:process.version,
    platform:process.platform,
    arch:process.arch
  },
  counts:COUNTS,
  iterations:ITERATIONS,
  results
};

await fs.mkdir(path.dirname(OUTPUT),{recursive:true});
await fs.writeFile(OUTPUT,JSON.stringify(report,null,2)+"\n","utf8");

console.table(results.map((row)=>({
  scenario:row.scenario,
  layers:row.layers,
  tracks:row.trackCount,
  median_ms:Number(row.medianMs.toFixed(3)),
  p95_ms:Number(row.p95Ms.toFixed(3))
})));
console.log("Wrote "+OUTPUT);
