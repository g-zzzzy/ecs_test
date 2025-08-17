#!/bin/bash

satellites=(5000 10000 15000 20000)
stations=(500 600 700 800 900 1000)
rounds=(10)

numWGs=(2)
numBlocks=(16)

for sta in "${stations[@]}"; do
  for sat in "${satellites[@]}"; do
    for round in "${rounds[@]}"; do
      for wg in "${numWGs[@]}"; do
        for block in "${numBlocks[@]}"; do
            echo "Running with Station: $sta, Satellite: $sat, Round: $round, WG: $wg, Block: $block"
            echo "==========================================="

            echo ">> ECS inter block"
            cd ../go_Weather_ITU-R
            go mod tidy
            go build ./scale/scale_ecs.go
            perf stat -e cache-references,cache-misses ./scale_ecs $sta $sat $round $wg $block 0 2>&1 | tee "../ecs_test/${round}times/result_ecs1_${sta}_${sat}_1_${block}.log"

            echo ">> KubeDemo"
            cd ../demo_kube
            go mod tidy
            go build ./scale/scale_kube.go
            perf stat -e cache-references,cache-misses ./scale_kube $sta $sat $round $block 2>&1 | tee "../ecs_test/${round}times/result_kube_${sta}_${sat}_1_${block}.log"
    
        done 
      done
    done
  done
done