#!/bin/bash

satellites=(500 600 700 800 900 1000 1100 1200 1300 1400 1500 1600 1700 1800 1900 2000)
stations=(500 600 700 800 900 1000)
rounds=(10)

numWGs=(2 4 8)
numBlocks=(2 4 8)

for sta in "${stations[@]}"; do
  for sat in "${satellites[@]}"; do
    for round in "${rounds[@]}"; do
      for wg in "${numWGs[@]}"; do
        for block in "${numBlocks[@]}"; do
            echo "Running with Station: $sta, Satellite: $sat, Round: $round, WG: $wg, Block: $block"
            echo "==========================================="

            echo ">> ECS 0"
            cd ../go_Weather_ITUR
            go mod tidy
            go build ./scale/scale_ecs.go
            numactl --cpunodebind=0 --membind=0 perf stat -e cache-references,cache-misses ./scale_ecs $sta $sat $round $wg $block 1 2>&1 | tee "../a_test/${round}times_numa/result_ecs1_${sta}_${sat}_${wg}_${block}.log"

            echo ">> ECS 1"
            cd ../go_Weather_ITUR
            go mod tidy
            go build ./scale/scale_ecs.go
            numactl --cpunodebind=0 --membind=0 perf stat -e cache-references,cache-misses ./scale_ecs $sta $sat $round $wg $block 0 2>&1 | tee "../a_test/${round}times_numa/result_ecs0_${sta}_${sat}_${wg}_${block}.log"
      
        done 
      done
    done
  done
done