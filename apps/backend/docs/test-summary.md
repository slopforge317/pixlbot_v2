# Test Summary

**Last run:** 2026-02-01
**Result:** Pending verification after Provider-Model-PricingVariant migration

## Test List

### API Authentication
- `test_api.test_auth.TestAuthEndpoint.test_valid_auth_returns_user`
- `test_api.test_auth.TestAuthEndpoint.test_missing_auth_header_returns_401`
- `test_api.test_auth.TestAuthEndpoint.test_invalid_auth_scheme_returns_401`
- `test_api.test_auth.TestAuthEndpoint.test_invalid_hash_returns_401`
- `test_api.test_auth.TestAuthEndpoint.test_expired_init_data_returns_401`
- `test_api.test_auth.TestAuthEndpoint.test_creates_new_user`
- `test_api.test_auth.TestAuthEndpoint.test_malformed_init_data_returns_401`

### API Providers
- `test_api.test_models.TestProvidersEndpoint.test_list_providers_unauthorized`
- `test_api.test_models.TestProvidersEndpoint.test_list_providers`
- `test_api.test_models.TestProvidersEndpoint.test_list_providers_filter_by_image`
- `test_api.test_models.TestProvidersEndpoint.test_list_providers_filter_by_video`
- `test_api.test_models.TestProvidersEndpoint.test_list_providers_empty`
- `test_api.test_models.TestProvidersEndpoint.test_list_providers_excludes_inactive_pricing`

### API Packages
- `test_api.test_packages.TestPackagesEndpoint.test_list_packages_unauthorized`
- `test_api.test_packages.TestPackagesEndpoint.test_list_packages`
- `test_api.test_packages.TestPackagesEndpoint.test_packages_sorted_by_price`
- `test_api.test_packages.TestPackagesEndpoint.test_package_price_formatted`
- `test_api.test_packages.TestPackagesEndpoint.test_list_packages_empty`

### API Generations
- `test_api.test_generations.TestCreateGeneration.test_create_generation_success`
- `test_api.test_generations.TestCreateGeneration.test_create_generation_insufficient_credits`
- `test_api.test_generations.TestCreateGeneration.test_create_generation_variant_not_found`
- `test_api.test_generations.TestCreateGeneration.test_create_generation_inactive_variant`
- `test_api.test_generations.TestCreateGeneration.test_create_generation_unauthorized`
- `test_api.test_generations.TestListGenerations.test_list_generations_success`
- `test_api.test_generations.TestListGenerations.test_list_generations_with_status_filter`
- `test_api.test_generations.TestListGenerations.test_list_generations_pagination`
- `test_api.test_generations.TestListGenerations.test_list_generations_unauthorized`
- `test_api.test_generations.TestGetGeneration.test_get_generation_success`
- `test_api.test_generations.TestGetGeneration.test_get_generation_not_found`
- `test_api.test_generations.TestGetGeneration.test_get_generation_other_user`
- `test_api.test_generations.TestGetGeneration.test_get_generation_unauthorized`

### API Webhook
- `test_api.test_webhook.TestWebhookEndpoint.test_webhook_valid_update`
- `test_api.test_webhook.TestWebhookEndpoint.test_webhook_invalid_secret`
- `test_api.test_webhook.TestWebhookEndpoint.test_webhook_missing_secret`
- `test_api.test_webhook.TestWebhookEndpoint.test_webhook_callback_query_update`
- `test_api.test_webhook.TestWebhookEndpoint.test_webhook_returns_ok_on_processing_error`
- `test_api.test_webhook.TestWebhookNotRegisteredWhenDisabled.test_webhook_not_available_when_disabled`

### Auth InitData Validation
- `test_services.test_auth.test_init_data.TestBuildDataCheckString.test_sorts_params_alphabetically`
- `test_services.test_auth.test_init_data.TestBuildDataCheckString.test_joins_with_newline`
- `test_services.test_auth.test_init_data.TestBuildDataCheckString.test_empty_params`
- `test_services.test_auth.test_init_data.TestCalculateHash.test_returns_hex_string`
- `test_services.test_auth.test_init_data.TestCalculateHash.test_hash_length`
- `test_services.test_auth.test_init_data.TestCalculateHash.test_same_input_same_hash`
- `test_services.test_auth.test_init_data.TestCalculateHash.test_different_input_different_hash`
- `test_services.test_auth.test_init_data.TestCalculateHash.test_uses_webappdata_key`
- `test_services.test_auth.test_init_data.TestParseInitData.test_parses_url_encoded_string`
- `test_services.test_auth.test_init_data.TestParseInitData.test_handles_special_characters`
- `test_services.test_auth.test_init_data.TestValidateInitData.test_valid_init_data`
- `test_services.test_auth.test_init_data.TestValidateInitData.test_empty_init_data_raises`
- `test_services.test_auth.test_init_data.TestValidateInitData.test_missing_hash_raises`
- `test_services.test_auth.test_init_data.TestValidateInitData.test_invalid_hash_raises`
- `test_services.test_auth.test_init_data.TestValidateInitData.test_expired_init_data_raises`
- `test_services.test_auth.test_init_data.TestValidateInitData.test_missing_auth_date_raises`
- `test_services.test_auth.test_init_data.TestValidateInitData.test_missing_user_raises`
- `test_services.test_auth.test_init_data.TestValidateInitData.test_invalid_user_json_raises`
- `test_services.test_auth.test_init_data.TestValidateInitData.test_user_without_required_fields_raises`
- `test_services.test_auth.test_init_data.TestValidateInitData.test_parses_optional_fields`

### Bot Handlers
- `test_bot.test_handlers.test_cmd_start_new_user`
- `test_bot.test_handlers.test_cmd_start_existing_user`
- `test_bot.test_handlers.test_cmd_start_with_utm`
- `test_bot.test_handlers.test_cmd_help`
- `test_bot.test_handlers.test_cmd_balance_registered_user`
- `test_bot.test_handlers.test_cmd_balance_unregistered_user`
- `test_bot.test_handlers.test_cmd_start_no_from_user`
- `test_bot.test_handlers.test_cmd_balance_no_from_user`

### Config
- `test_config.test_settings_defaults`

### Database Models
- `test_db.test_models.test_create_user`
- `test_db.test_models.test_create_credit_package`
- `test_db.test_models.test_create_provider_with_model_and_pricing`
- `test_db.test_models.test_create_payment`
- `test_db.test_models.test_create_generation_job`
- `test_db.test_models.test_create_transaction`

### Database Repositories
- `test_db.test_repositories.test_user_get_or_create_new`
- `test_db.test_repositories.test_user_get_or_create_existing`
- `test_db.test_repositories.test_user_get_by_telegram_id`
- `test_db.test_repositories.test_user_balance`
- `test_db.test_repositories.test_generation_job_get_user_jobs`
- `test_db.test_repositories.test_generation_job_get_pending`
- `test_db.test_repositories.test_provider_get_all_active_with_models`
- `test_db.test_repositories.test_provider_get_by_gen_type`
- `test_db.test_repositories.test_ai_model_get_by_api_model_id`
- `test_db.test_repositories.test_ai_model_get_with_variants`
- `test_db.test_repositories.test_pricing_variant_get_by_id_with_model`
- `test_db.test_repositories.test_pricing_variant_get_active_by_model_id`
- `test_db.test_repositories.test_credit_package_get_active`
- `test_db.test_repositories.test_credit_package_get_active_ordered_by_price`
- `test_db.test_repositories.test_transaction_get_user_transactions`
- `test_db.test_repositories.test_transaction_get_by_type`
- `test_db.test_repositories.test_transaction_create_deposit`
- `test_db.test_repositories.test_transaction_create_withdrawal`
- `test_db.test_repositories.test_transaction_create_refund`

### KIE API Client
- `test_services.test_kie.test_client.test_create_task_success`
- `test_services.test_kie.test_client.test_create_task_auth_error`
- `test_services.test_kie.test_client.test_create_task_insufficient_credits`
- `test_services.test_kie.test_client.test_create_task_rate_limit`
- `test_services.test_kie.test_client.test_get_task_status_success`
- `test_services.test_kie.test_client.test_get_task_status_generating`
- `test_services.test_kie.test_client.test_client_context_manager`

### KIE API Schemas
- `test_services.test_kie.test_schemas.test_create_task_request_with_input_model`
- `test_services.test_kie.test_schemas.test_create_task_request_with_dict`
- `test_services.test_kie.test_schemas.test_create_task_response_success`
- `test_services.test_kie.test_schemas.test_create_task_response_error`
- `test_services.test_kie.test_schemas.test_task_status_data_success`
- `test_services.test_kie.test_schemas.test_task_status_data_generating`
- `test_services.test_kie.test_schemas.test_task_status_data_failed`
- `test_services.test_kie.test_schemas.test_task_status_response`
- `test_services.test_kie.test_schemas.test_generation_result_from_task_status`
- `test_services.test_kie.test_schemas.test_kie_task_state_enum`

### KIE API Service
- `test_services.test_kie.test_service.test_create_generation`
- `test_services.test_kie.test_service.test_get_result_success`
- `test_services.test_kie.test_service.test_get_result_still_processing`
- `test_services.test_kie.test_service.test_get_result_failed`
- `test_services.test_kie.test_service.test_wait_for_result_immediate_success`
- `test_services.test_kie.test_service.test_wait_for_result_polling`
- `test_services.test_kie.test_service.test_wait_for_result_timeout`
- `test_services.test_kie.test_service.test_generate_and_wait`

### Generation Service
- `test_services.test_generation.TestBuildContext.test_build_context_image`
- `test_services.test_generation.TestBuildContext.test_build_context_video`
- `test_services.test_generation.TestHandleError.test_handle_error_updates_job_and_refunds`
- `test_services.test_generation.TestHandleTimeout.test_handle_timeout_updates_job_and_refunds`
- `test_services.test_generation.TestExecuteGeneration.test_execute_generation_success`
- `test_services.test_generation.TestExecuteGeneration.test_execute_generation_with_variant_values`
- `test_services.test_generation.TestExecuteGeneration.test_execute_generation_kie_failure`
- `test_services.test_generation.TestExecuteGeneration.test_execute_generation_timeout`
- `test_services.test_generation.TestProcessGenerationImpl.test_process_generation_job_not_found`
- `test_services.test_generation.TestProcessGenerationImpl.test_process_generation_wrong_status`
- `test_services.test_generation.TestProcessGenerationImpl.test_process_generation_full_flow_success`
- `test_services.test_generation.TestProcessGenerationImpl.test_process_generation_full_flow_error_with_refund`
