namespace MerzoOptimizer.Core.Dispatching;

public sealed class AsyncOperationDispatcher : IAsyncOperationDispatcher, IDisposable
{
    private readonly SemaphoreSlim _gate;

    public AsyncOperationDispatcher(int maxConcurrency = 2)
    {
        if (maxConcurrency < 1)
            throw new ArgumentOutOfRangeException(nameof(maxConcurrency));

        _gate = new SemaphoreSlim(maxConcurrency, maxConcurrency);
    }

    public event EventHandler<OperationStateChangedEventArgs>? StateChanged;

    public async Task RunAsync(
        string operationName,
        Func<CancellationToken, Task> operation,
        CancellationToken cancellationToken = default)
    {
        await RunAsync<object?>(
            operationName,
            async token =>
            {
                await operation(token).ConfigureAwait(false);
                return null;
            },
            cancellationToken).ConfigureAwait(false);
    }

    public async Task<T> RunAsync<T>(
        string operationName,
        Func<CancellationToken, Task<T>> operation,
        CancellationToken cancellationToken = default)
    {
        StateChanged?.Invoke(this, new(operationName, OperationState.Queued));

        try
        {
            await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            StateChanged?.Invoke(this, new(operationName, OperationState.Cancelled));
            throw;
        }

        try
        {
            StateChanged?.Invoke(this, new(operationName, OperationState.Running));
            var result = await Task.Run(
                () => operation(cancellationToken),
                cancellationToken).ConfigureAwait(false);
            StateChanged?.Invoke(this, new(operationName, OperationState.Completed));
            return result;
        }
        catch (OperationCanceledException)
        {
            StateChanged?.Invoke(this, new(operationName, OperationState.Cancelled));
            throw;
        }
        catch (Exception ex)
        {
            StateChanged?.Invoke(this, new(operationName, OperationState.Failed, ex.Message));
            throw;
        }
        finally
        {
            _gate.Release();
        }
    }

    public void Dispose() => _gate.Dispose();
}
