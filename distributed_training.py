import os
from task_spec import get_task_spec
from trainer import Trainer
from evaluator import Evaluator
import tensorflow as tf


class DistributedTrainer(Trainer):
    """
    Example of class to run a distributed trainer with a dataset. The only tweak is to set
    the dataset to use shuffle and task_spec.
    Note the constructor receives a function to build the model, see
    model_fn_example(dataset_tensor, batch_size) for more information about this function.
    """

    def __init__(self, log_dir, dataset, model_fn, task_spec, **kwargs):
        self.model_fn = model_fn
        super(DistributedTrainer, self).__init__(log_dir=log_dir, dataset=dataset,
                                                 task_spec=task_spec, **kwargs)

    def create_graph(self, dataset_tensor, batch_size):
        return self.model_fn(dataset_tensor=dataset_tensor,
                             batch_size=batch_size,
                             evaluation=False)

    def step(self, session, graph_data):
        session.run(graph_data)


class DistributedEvaluator(Evaluator):
    """
    Example of distributed evaluator. The only tweak is to set the dataset to use batch_size=1 and
    num_epochs=1. This way we guarantee the model see all the examples only once.
    Note the constructor receives a function to build the model, see
    model_fn_example(dataset_tensor, batch_size) for more information about this function.
    """

    def __init__(self, log_dir, dataset, model_fn, **kwargs):
        self.model_fn = model_fn
        output_path = os.path.join(log_dir, 'eval')
        super(DistributedEvaluator, self).__init__(checkpoints_dir=log_dir, output_path=output_path,
                                                   dataset=dataset, **kwargs)

    def create_graph(self, dataset_tensor, batch_size):
        self.graph_data = self.model_fn(dataset_tensor=dataset_tensor,
                                        batch_size=batch_size,
                                        evaluation=False)
        return self.graph_data


def model_fn_example(dataset_tensor, batch_size, evaluation):
    """
    Example of the signature of the function that creates the model used in the
    Trainer and Evaluator.
    :param tf.Tensor dataset_tensor: the tensor created from the dataset
    :param int batch_size: the batch size for the model, the same used in the dataset.
    :param bool evaluation: True if this model is for evaluation, False if it is for training.
    :return: returns the graph data, this is what session.run will execute during the training,
    for the test it will only execute the summary operator.
    """
    graph_data = None
    return graph_data


def launch_train_evaluation(model_fn, log_dir, epochs, train_batch_size, train_datasest,
                            eval_dataset, trainer_class=DistributedTrainer,
                            evaluator_class=DistributedEvaluator):
    """
    Launchs the training with an evaluator in the last worker. Only call this from distributed or it
    will fail.
    :param model_fn: function to create the model
    :param log_dir: directory for the logs/checkpoints
    :param epochs: number of epochs to perform the training
    :param train_batch_size: batch size of the trainer
    :param train_datasest: dataset for training
    :param eval_dataset: dataset for evaluation
    :param trainer_class: custom trainer, defaults to DistributedTrainer
    :param evaluator_class: custom trainer, defaults to DistributedEvaluator
    """
    task_spec = get_task_spec(with_evaluator=True)
    if task_spec.num_workers <= 1:
        raise ValueError('More than one worker needed in order to perform a continuos evaluation')
    if task_spec.join_if_ps():
        return  # join if it is a parameters server and do nothing else
    if task_spec.is_evaluator():
        # run evaluator
        evaluator = evaluator_class(log_dir=log_dir,
                                    dataset=eval_dataset,
                                    model_fn=model_fn)
        evaluator.run()
    else:
        trainer = trainer_class(log_dir=log_dir,
                                dataset=train_datasest,
                                model_fn=model_fn,
                                task_spec=task_spec)
        trainer.run(batch_size=train_batch_size, epochs=epochs)
