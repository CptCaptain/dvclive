import os

import pytest

from dvclive import Live
from dvclive.plots.metric import Metric
from dvclive.utils import parse_metrics

try:
    from dvclive.keras import DVCLiveCallback
except ImportError:
    pytest.skip("skipping keras tests", allow_module_level=True)


@pytest.fixture()
def xor_model():
    import numpy as np
    import tensorflow as tf

    def make():
        x = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
        y = np.array([[0], [1], [1], [0]])

        model = tf.keras.Sequential()
        model.add(tf.keras.layers.Dense(8, input_dim=2))
        model.add(tf.keras.layers.Activation("relu"))
        model.add(tf.keras.layers.Dense(1))
        model.add(tf.keras.layers.Activation("sigmoid"))

        model.compile(loss="binary_crossentropy", optimizer="sgd", metrics=["accuracy"])

        return model, x, y

    return make


def test_keras_callback(tmp_dir, xor_model, mocker):
    model, x, y = xor_model()

    callback = DVCLiveCallback()
    live = callback.live
    spy = mocker.spy(live, "end")
    model.fit(
        x,
        y,
        epochs=1,
        batch_size=1,
        validation_split=0.2,
        callbacks=[callback],
    )
    spy.assert_called_once()

    assert os.path.exists("dvclive")
    logs, _ = parse_metrics(callback.live)

    scalars = os.path.join(callback.live.plots_dir, Metric.subfolder)
    assert os.path.join(scalars, "train", "accuracy.tsv") in logs
    assert os.path.join(scalars, "eval", "accuracy.tsv") in logs


def test_keras_callback_pass_logger():
    logger = Live("train_logs")

    assert DVCLiveCallback().live is not logger
    assert DVCLiveCallback(live=logger).live is logger


@pytest.mark.parametrize("save_weights_only", [True, False])
def test_keras_model_file(tmp_dir, xor_model, mocker, save_weights_only):
    model, x, y = xor_model()
    save = mocker.spy(model, "save")
    save_weights = mocker.spy(model, "save_weights")

    live_callback = DVCLiveCallback(
        model_file="model.h5", save_weights_only=save_weights_only
    )
    log_artifact = mocker.patch.object(live_callback.live, "log_artifact")
    model.fit(
        x,
        y,
        epochs=1,
        batch_size=1,
        callbacks=[live_callback],
    )
    assert save.call_count != save_weights_only
    assert save_weights.call_count == save_weights_only
    log_artifact.assert_called_with(live_callback.model_file)


@pytest.mark.parametrize("save_weights_only", [True, False])
def test_keras_load_model_on_resume(tmp_dir, xor_model, mocker, save_weights_only):
    model, x, y = xor_model()

    if save_weights_only:
        model.save_weights("model.h5")
    else:
        model.save("model.h5")

    load_weights = mocker.spy(model, "load_weights")

    model.fit(
        x,
        y,
        epochs=1,
        batch_size=1,
        callbacks=[
            DVCLiveCallback(
                model_file="model.h5",
                save_weights_only=save_weights_only,
                resume=True,
            )
        ],
    )

    assert load_weights.call_count == save_weights_only


def test_keras_no_resume_skip_load(tmp_dir, xor_model, mocker):
    model, x, y = xor_model()

    model.save_weights("model.h5")

    load_weights = mocker.spy(model, "load_weights")

    model.fit(
        x,
        y,
        epochs=1,
        batch_size=1,
        callbacks=[
            DVCLiveCallback(
                model_file="model.h5",
                save_weights_only=True,
                resume=False,
            )
        ],
    )

    assert load_weights.call_count == 0


def test_keras_no_existing_model_file_skip_load(tmp_dir, xor_model, mocker):
    model, x, y = xor_model()

    load_weights = mocker.spy(model, "load_weights")

    model.fit(
        x,
        y,
        epochs=1,
        batch_size=1,
        callbacks=[
            DVCLiveCallback(
                model_file="model.h5",
                save_weights_only=True,
                resume=True,
            )
        ],
    )

    assert load_weights.call_count == 0


def test_keras_none_model_file_skip_load(tmp_dir, xor_model, mocker):
    model, x, y = xor_model()

    model.save_weights("model.h5")

    load_weights = mocker.spy(model, "load_weights")

    model.fit(
        x,
        y,
        epochs=1,
        batch_size=1,
        callbacks=[
            DVCLiveCallback(
                save_weights_only=True,
                resume=True,
            )
        ],
    )

    assert load_weights.call_count == 0
