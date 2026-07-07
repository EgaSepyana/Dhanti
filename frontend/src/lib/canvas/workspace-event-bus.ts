type Listener = (event: string, data: unknown) => void;

/** In-memory pub/sub so bridge.workspace.emit() from one canvas reaches
 * bridge.events.subscribe() handlers in every other canvas on the page. */
class WorkspaceEventBus {
  private listeners = new Set<Listener>();

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  emit(event: string, data: unknown): void {
    this.listeners.forEach((listener) => listener(event, data));
  }
}

export const workspaceEventBus = new WorkspaceEventBus();
