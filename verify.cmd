@echo off
setlocal enabledelayedexpansion

REM Simple helper
:fail
echo ❌ %1
exit /b 1

:pass
echo ✅ %1
exit /b 0

echo == Checking structure ==
for %%F in (
  lambda_app\handler.py lambda_app\settings.py lambda_app\generators.py
  lambda_app\s3_uploader.py lambda_app\metrics.py lambda_app\util.py
  runner\experiment_runner.py runner\logs_insights_queries.py runner\summarize_results.py
  tests\test_generators.py tests\test_uploader.py README.md requirements.txt
) do (
  if not exist "%%F" (
    echo ❌ Missing: %%F
    exit /b 1
  )
)
echo ✅ All required files exist

echo == Checking handler & env vars ==
findstr /R /C:"def[ ]*handler *(event,*context" lambda_app\handler.py >nul || (echo ❌ handler(event, context) not found & exit /b 1)
findstr /R "WORKLOAD OUTPUT_BUCKET BATCH_EVENTS EVENT_BYTES MULTIPART_MB OBJECT_MB MEMORY_MB RESERVED_CONCURRENCY" lambda_app\*.py >nul || (echo ❌ Missing required env var usage & exit /b 1)
echo ✅ Handler + env vars OK

echo == Checking EMF log builder ==
findstr /C:"CloudWatchMetrics" lambda_app\metrics.py >nul || (echo ❌ EMF CloudWatchMetrics block missing & exit /b 1)
findstr /C:"LambdaS3Study" lambda_app\metrics.py >nul || (echo ❌ Namespace LambdaS3Study missing & exit /b 1)
findstr /C:"workload" lambda_app\metrics.py lambda_app\handler.py >nul || (echo ❌ Required Dimensions missing & exit /b 1)
findstr /C:"latency_ms" lambda_app\metrics.py lambda_app\handler.py >nul || (echo ❌ latency_ms metric missing & exit /b 1)
findstr /C:"object_bytes" lambda_app\metrics.py lambda_app\handler.py >nul || (echo ❌ object_bytes metric missing & exit /b 1)
findstr /C:"events_generated" lambda_app\metrics.py lambda_app\handler.py >nul || (echo ❌ events_generated metric missing & exit /b 1)
echo ✅ EMF fields present (check runtime for single-line JSON)

echo == Checking events path ==
findstr /C:"BATCH_EVENTS" lambda_app\handler.py >nul || (echo ❌ BATCH_EVENTS missing in handler & exit /b 1)
findstr /C:"EVENT_BYTES" lambda_app\handler.py >nul || (echo ❌ EVENT_BYTES missing in handler & exit /b 1)
findstr /I "put_object" lambda_app\s3_uploader.py lambda_app\handler.py >nul || (echo ❌ put_object not found & exit /b 1)
echo ✅ Events path wiring OK

echo == Checking batch path ==
findstr /C:"create_multipart_upload" lambda_app\s3_uploader.py lambda_app\handler.py >nul || (echo ❌ create_multipart_upload missing & exit /b 1)
findstr /C:"upload_part" lambda_app\s3_uploader.py lambda_app\handler.py >nul || (echo ❌ upload_part missing & exit /b 1)
findstr /C:"complete_multipart_upload" lambda_app\s3_uploader.py lambda_app\handler.py >nul || (echo ❌ complete_multipart_upload missing & exit /b 1)
findstr /C:"MULTIPART_MB" lambda_app\*.py >nul || (echo ❌ MULTIPART_MB not wired & exit /b 1)
echo ✅ Batch path multipart OK

echo == Checking runner ==
findstr /C:"argparse" runner\experiment_runner.py >nul || (echo ❌ argparse missing & exit /b 1)
findstr /C:"--function-prefix" runner\experiment_runner.py >nul || (echo ❌ --function-prefix flag missing & exit /b 1)
findstr /C:"list_functions" runner\experiment_runner.py >nul || (echo ❌ list_functions not used & exit /b 1)
echo ✅ Runner CLI and discovery OK

echo == Checking Logs Insights queries ==
findstr /C:"pct(latency_ms,95)" runner\logs_insights_queries.py >nul || (echo ❌ p95 calc missing & exit /b 1)
findstr /C:"throughput_obj_per_s" runner\logs_insights_queries.py >nul || (echo ❌ throughput calc missing & exit /b 1)
findstr /C:"object_bytes" runner\logs_insights_queries.py >nul || (echo ❌ object_bytes sum missing & exit /b 1)
echo ✅ Logs Insights queries OK

echo == Running tests ==
pytest -q
if errorlevel 1 (
  echo ❌ Tests failing
  exit /b 1
) else (
  echo ✅ All tests passed
)

echo 🎉 Verification complete.
