# ruff: noqa: F811

from docetl.operations.map import MapOperation
from tests.conftest import (
    api_wrapper as api_wrapper,
    map_config_with_batching as map_config_with_batching,
    default_model as default_model,
    max_threads as max_threads,
    map_sample_data as map_sample_data,
    map_sample_data_large as map_sample_data_large,
    map_config as map_config,
    test_map_operation_instance as test_map_operation_instance,
    map_config_with_drop_keys as map_config_with_drop_keys,
    map_sample_data_with_extra_keys as map_sample_data_with_extra_keys,
    map_config_with_drop_keys_no_prompt as map_config_with_drop_keys_no_prompt,
)
import pytest
import docetl


def test_map_operation(
    test_map_operation_instance,
    map_sample_data,
):
    results, cost = test_map_operation_instance.execute(map_sample_data)

    assert len(results) == len(map_sample_data)
    assert all("sentiment" in result for result in results)
    valid_sentiments = ["positive", "negative", "neutral"]
    assert all(
        any(vs in result["sentiment"] for vs in valid_sentiments) for result in results
    )


def test_map_operation_empty_input(map_config, default_model, max_threads, api_wrapper):
    operation = MapOperation(api_wrapper, map_config, default_model, max_threads)
    results, cost = operation.execute([])

    assert len(results) == 0
    assert cost == 0


def test_map_operation_with_drop_keys(
    map_config_with_drop_keys,
    default_model,
    max_threads,
    map_sample_data_with_extra_keys,
    api_wrapper,
):
    map_config_with_drop_keys["bypass_cache"] = True
    operation = MapOperation(
        api_wrapper, map_config_with_drop_keys, default_model, max_threads
    )
    results, cost = operation.execute(map_sample_data_with_extra_keys)

    assert len(results) == len(map_sample_data_with_extra_keys)
    assert all("sentiment" in result for result in results)
    assert all("original_sentiment" in result for result in results)
    assert all("to_be_dropped" not in result for result in results)
    assert all(
        result["sentiment"] in ["positive", "negative", "neutral"] for result in results
    )

    assert cost > 0


def test_map_operation_with_drop_keys_no_prompt(
    map_config_with_drop_keys_no_prompt,
    default_model,
    max_threads,
    map_sample_data_with_extra_keys,
    api_wrapper,
):
    operation = MapOperation(
        api_wrapper, map_config_with_drop_keys_no_prompt, default_model, max_threads
    )
    results, cost = operation.execute(map_sample_data_with_extra_keys)

    assert len(results) == len(map_sample_data_with_extra_keys)
    assert all("to_be_dropped" not in result for result in results)
    assert all("text" in result for result in results)
    assert all("original_sentiment" in result for result in results)
    assert cost == 0  # No LLM calls should be made


def test_map_operation_with_batching(
    map_config_with_batching,
    default_model,
    max_threads,
    map_sample_data,
    api_wrapper,
):
    operation = MapOperation(
        api_wrapper, map_config_with_batching, default_model, max_threads
    )
    results, cost = operation.execute(map_sample_data)

    assert len(results) == len(map_sample_data)
    assert all("sentiment" in result for result in results)
    valid_sentiments = ["positive", "negative", "neutral"]
    assert all(
        any(vs in result["sentiment"] for vs in valid_sentiments) for result in results
    )


def test_map_operation_with_empty_input(
    map_config_with_batching, default_model, max_threads, api_wrapper
):
    operation = MapOperation(
        api_wrapper, map_config_with_batching, default_model, max_threads
    )
    results, cost = operation.execute([])

    assert len(results) == 0
    assert cost == 0


def test_map_operation_with_large_max_batch_size(
    map_config_with_batching,
    default_model,
    max_threads,
    map_sample_data,
    api_wrapper,
):
    map_config_with_batching["max_batch_size"] = 5  # Set batch size larger than data
    operation = MapOperation(
        api_wrapper, map_config_with_batching, default_model, max_threads
    )
    results, cost = operation.execute(map_sample_data)

    assert len(results) == len(map_sample_data)


def test_map_operation_with_word_count_tool(
    map_config_with_tools, synthetic_data, api_wrapper
):
    operation = MapOperation(api_wrapper, map_config_with_tools, "gpt-4o-mini", 4)
    results, cost = operation.execute(synthetic_data)

    assert len(results) == len(synthetic_data)
    assert all("word_count" in result for result in results)
    assert [result["word_count"] for result in results] == [5, 6, 5, 1]


@pytest.fixture
def simple_map_config():
    return {
        "name": "simple_sentiment_analysis",
        "type": "map",
        "prompt": "Analyze the sentiment of the following text: '{{ input.text }}'. Classify it as either positive, negative, or neutral.",
        "output": {"schema": {"sentiment": "string"}},
        "model": "gpt-4o-mini",
    }


@pytest.fixture
def simple_sample_data():
    import random
    import string

    def generate_random_text(length):
        return "".join(
            random.choice(
                string.ascii_letters + string.digits + string.punctuation + " "
            )
            for _ in range(length)
        )

    return [
        {"text": generate_random_text(random.randint(20, 100000))},
        {"text": generate_random_text(random.randint(20, 100000))},
        {"text": generate_random_text(random.randint(20, 100000))},
    ]


# @pytest.mark.flaky(reruns=2)
# def test_map_operation_with_timeout(simple_map_config, simple_sample_data, api_wrapper):
#     # Add timeout to the map configuration
#     map_config_with_timeout = {
#         **simple_map_config,
#         "timeout": 1,
#         "max_retries_per_timeout": 0,
#         "bypass_cache": True,
#     }

#     operation = MapOperation(api_wrapper, map_config_with_timeout, "gpt-4o-mini", 4)

#     # Execute the operation and expect empty results
#     results, cost = operation.execute(simple_sample_data)
#     assert len(results) == 0


def test_map_operation_with_gleaning(simple_map_config, map_sample_data, api_wrapper):
    # Add gleaning configuration to the map configuration
    map_config_with_gleaning = {
        **simple_map_config,
        "gleaning": {
            "num_rounds": 2,
            "validation_prompt": "Review the sentiment analysis. Is it accurate? If not, suggest improvements.",
        },
        "bypass_cache": True,
    }

    operation = MapOperation(api_wrapper, map_config_with_gleaning, "gpt-4o-mini", 4)

    # Execute the operation
    results, cost = operation.execute(map_sample_data)

    # Assert that we have results for all input items
    assert len(results) == len(map_sample_data)

    # Check that all results have a sentiment
    assert all("sentiment" in result for result in results)

    # Verify that all sentiments are valid
    valid_sentiments = ["positive", "negative", "neutral"]
    assert all(
        any(vs in result["sentiment"] for vs in valid_sentiments) for result in results
    )

def test_map_with_enum_output(simple_map_config, map_sample_data, api_wrapper):
    map_config_with_enum_output = {
        **simple_map_config,
        "output": {"schema": {"sentiment": "enum[positive, negative, neutral]"}},
        "bypass_cache": True,
    }

    operation = MapOperation(api_wrapper, map_config_with_enum_output, "gpt-4o-mini", 4)
    results, cost = operation.execute(map_sample_data)

    assert len(results) == len(map_sample_data)
    assert all("sentiment" in result for result in results)
    assert all(result["sentiment"] in ["positive", "negative", "neutral"] for result in results)

    # # Try gemini model
    # map_config_with_enum_output["model"] = "gemini/gemini-1.5-flash"
    # operation = MapOperation(api_wrapper, map_config_with_enum_output, "gemini/gemini-1.5-flash", 4)
    # results, cost = operation.execute(map_sample_data)

    # assert len(results) == len(map_sample_data)
    # assert all("sentiment" in result for result in results)
    # assert all(result["sentiment"] in ["positive", "negative", "neutral"] for result in results)
    # assert cost > 0

    # Try list of enum types
    map_config_with_enum_output["output"] = {"schema": {"possible_sentiments": "list[enum[positive, negative, neutral]]"}}
    operation = MapOperation(api_wrapper, map_config_with_enum_output, "gpt-4o-mini", 4)
    results, cost = operation.execute(map_sample_data)
    assert cost > 0

    assert len(results) == len(map_sample_data)
    assert all("possible_sentiments" in result for result in results)
    for result in results:
        for ps in result["possible_sentiments"]:
            assert ps in ["positive", "negative", "neutral"]

    

def test_map_operation_with_batch_processing(simple_map_config, map_sample_data, api_wrapper):
    # Add batch processing configuration
    map_config_with_batch = {
        **simple_map_config,
        "max_batch_size": 2,
        "batch_prompt": """Analyze the sentiment of each of the following texts:
{% for input in inputs %}
Text {{loop.index}}: {{input.text}}
{% endfor %}

For each text, provide a sentiment analysis in the following format:
[
  {"sentiment": "positive/negative/neutral"}
]""",
        "bypass_cache": True,
        "validate": ["output['sentiment'] in ['positive', 'negative', 'neutral']"],
        "num_retries_on_validate_failure": 1,
    }

    operation = MapOperation(api_wrapper, map_config_with_batch, "gpt-4o-mini", 4)

    # Execute the operation
    results, cost = operation.execute(map_sample_data)

    # Assert that we have results for all input items
    assert len(results) == len(map_sample_data)

    # Check that all results have a sentiment
    assert all("sentiment" in result for result in results)

    # Verify that all sentiments are valid
    valid_sentiments = ["positive", "negative", "neutral"]
    assert all(
        any(vs in result["sentiment"] for vs in valid_sentiments) for result in results
    )

def test_map_operation_with_larger_batch(simple_map_config, map_sample_data_with_extra_keys, api_wrapper):
    # Add batch processing configuration with larger batch size
    map_config_with_large_batch = {
        **simple_map_config,
        "max_batch_size": 4,  # Process 4 items at a time
        "batch_prompt": """Analyze the sentiment of each of the following texts:
{% for input in inputs %}
Text {{loop.index}}: {{input.text}}
{% endfor %}

For each text, provide a sentiment analysis in the following format:
[
  {"sentiment": "positive/negative/neutral"}
]""",
        "bypass_cache": True,
        "validate": ["output['sentiment'] in ['positive', 'negative', 'neutral']"],
        "num_retries_on_validate_failure": 1,
    }

    operation = MapOperation(api_wrapper, map_config_with_large_batch, "gpt-4o-mini", 64)

    # Execute the operation with the larger dataset
    results, cost = operation.execute(map_sample_data_with_extra_keys * 4)

    # Assert that we have results for all input items
    assert len(results) == len(map_sample_data_with_extra_keys * 4)

    # Check that all results have a sentiment
    assert all("sentiment" in result for result in results)

    # Verify that all sentiments are valid
    valid_sentiments = ["positive", "negative", "neutral"]
    assert all(
        any(vs in result["sentiment"] for vs in valid_sentiments) for result in results
    )

def test_map_operation_with_max_tokens(simple_map_config, map_sample_data, api_wrapper):
    # Add litellm_completion_kwargs configuration with max_tokens
    map_config_with_max_tokens = {
        **simple_map_config,
        "litellm_completion_kwargs": {
            "max_tokens": 10
        },
        "bypass_cache": True
    }

    operation = MapOperation(api_wrapper, map_config_with_max_tokens, "gpt-4o-mini", 4)

    # Execute the operation
    results, cost = operation.execute(map_sample_data)

    # Assert that we have results for all input items
    assert len(results) == len(map_sample_data)

    # Check that all results have a sentiment
    assert all("sentiment" in result for result in results)

    # Verify that all sentiments are valid
    valid_sentiments = ["positive", "negative", "neutral"]
    assert all(
        any(vs in result["sentiment"] for vs in valid_sentiments) for result in results
    )

    # Since we limited max_tokens to 10, each response should be relatively short
    # The sentiment field should contain just the sentiment value without much extra text
    assert all(len(result["sentiment"]) <= 20 for result in results)
    
def test_map_operation_with_verbose(simple_map_config, map_sample_data, api_wrapper):
    # Add verbose configuration
    map_config_with_verbose = {
        **simple_map_config,
        "verbose": True,
        "bypass_cache": True
    }

    operation = MapOperation(api_wrapper, map_config_with_verbose, "gpt-4o-mini", 4)

    # Execute the operation
    results, cost = operation.execute(map_sample_data)

    # Assert that we have results for all input items
    assert len(results) == len(map_sample_data)

    # Check that all results have a sentiment
    assert all("sentiment" in result for result in results)

    # Verify that all sentiments are valid
    valid_sentiments = ["positive", "negative", "neutral"]
    assert all(
        any(vs in result["sentiment"] for vs in valid_sentiments) for result in results
    )

def test_map_operation_partial_checkpoint(
    tmp_path, simple_map_config, default_model, max_threads, map_sample_data, api_wrapper
):
    """
    Test that MapOperation flushes partial results to disk when checkpoint_partial is enabled.
    
    This test:
    - Sets the intermediate_dir to a temporary directory.
    - Enables flush_partial_results in the operation config.
    - Executes the map operation.
    - Verifies that a subfolder named '<operation_name>_batches' is created.
    - Verifies that at least one partial checkpoint file (e.g. batch_0.json) is present and contains valid JSON.
    """
    import json
    import os

    # Set up the intermediate directory in the temporary path.
    intermediate_dir = tmp_path / "intermediate_results"
    intermediate_dir.mkdir()

    # Enable partial checkpointing in the config.
    map_config = {
        **simple_map_config,
        "flush_partial_results": True,
        "bypass_cache": True
    }

    # Set the runner's intermediate_dir.
    # In our tests, 'api_wrapper' acts as the runner.
    api_wrapper.intermediate_dir = str(intermediate_dir)

    # Create and run the MapOperation.
    operation = MapOperation(api_wrapper, map_config, default_model, max_threads)
    results, cost = operation.execute(map_sample_data)

    # Determine the expected batch folder based on the operation name.
    op_name = map_config["name"]
    batch_folder = intermediate_dir / f"{op_name}_batches"
    assert batch_folder.exists(), f"Partial checkpoint folder {batch_folder} does not exist"

    # List all partial checkpoint files (expecting names like "batch_0.json", etc.)
    batch_files = sorted(batch_folder.glob("batch_*.json"))
    assert batch_files, "No partial checkpoint files were created"

    # Check the first batch file contains valid, non-empty JSON data.
    with open(batch_files[0], "r") as f:
        data = json.load(f)
    if map_sample_data:  # Only check if there was input
        assert isinstance(data, list), "Data in checkpoint file is not a list"
        assert data, "Partial checkpoint file is empty"


def test_map_operation_with_calibration(simple_map_config, map_sample_data, api_wrapper):
    """
    Test that MapOperation performs calibration when enabled.
    
    This test:
    - Enables calibration in the map config.
    - Executes the map operation with calibration enabled.
    - Verifies that results are returned for all input items.
    - Verifies that the calibration process doesn't break the normal operation.
    """
    # Create a map config with calibration enabled
    map_config_with_calibration = {
        **simple_map_config,
        "calibrate": True,
        "num_calibration_docs": 3,  # Small number for testing
        "bypass_cache": True
    }

    operation = MapOperation(api_wrapper, map_config_with_calibration, "gpt-4o-mini", 4)
    
    # Execute the operation with calibration
    results, cost = operation.execute(map_sample_data)

    # Assert that we have results for all input items
    assert len(results) == len(map_sample_data)

    # Check that all results have a sentiment
    assert all("sentiment" in result for result in results)

    # Verify that all sentiments are valid
    valid_sentiments = ["positive", "negative", "neutral"]
    assert all(
        any(vs in result["sentiment"] for vs in valid_sentiments) for result in results
    )

    # Verify that cost is greater than 0 (includes calibration cost)
    assert cost > 0


def test_map_operation_calibration_with_larger_sample(simple_map_config, map_sample_data_large, api_wrapper):
    """
    Test calibration with a larger dataset to ensure proper sampling.
    """
    # Create a map config with calibration enabled
    map_config_with_calibration = {
        **simple_map_config,
        "calibrate": True,
        "num_calibration_docs": 5,  # Test with 5 docs from larger dataset
        "bypass_cache": True
    }

    operation = MapOperation(api_wrapper, map_config_with_calibration, "gpt-4o-mini", 4)
    
    # Execute the operation with calibration on larger dataset
    results, cost = operation.execute(map_sample_data_large)

    # Assert that we have results for all input items
    assert len(results) == len(map_sample_data_large)

    # Check that all results have a sentiment
    assert all("sentiment" in result for result in results)

    # Verify that all sentiments are valid
    valid_sentiments = ["positive", "negative", "neutral"]
    assert all(
        any(vs in result["sentiment"] for vs in valid_sentiments) for result in results
    )

    # Verify that cost is greater than 0
    assert cost > 0