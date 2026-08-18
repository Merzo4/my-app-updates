namespace MerzoOptimizer.Core.Dispatching;

public interface IAsyncOperationDispatcher
{
    event EventHandler<OperationStateChangedEventArgs>? StateChanged;

    Task RunAsync(
        string operationName,
        Func<CancellationToken, Task> operation,
        CancellationToken cancellationToken = default);

    Task<T> RunAsync<T>(
        string operationName,
        Func<CancellationToken, Task<T>> operation,
        CancellationToken cancellationToken = default);
}

public sealed class OperationStateChangedEventArgs : EventArgs
{
    public OperationStateChangedEventArgs(
        string operationName,
        OperationState state,
        string? error = null)
    {
        OperationName = operationName;
        State = state;
        Error = error;
    }

    public string OperationName { get; }
    public OperationState State { get; }
    public string? Error { get; }
}

public enum OperationState
{
    Queued,
    Running,
    Completed,
    Failed,
    Cancelled
}
