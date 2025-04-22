# Sample App

This is a sample application for the Stock Exchange training program.

## Quick Tip: Connecting to the Server via Command Line (Linux)

1. **Connect to the Server**  
    Use `telnet` to connect to the server:
    ```bash
    telnet <server_address> <port>
    ```
    Replace `<server_address>` and `<port>` with the appropriate values.

2. **Send Messages**  
    Once connected, type your message and press `Enter` to send it to the server.

3. **View Responses**  
    The server will echo back the messages you send.

### Example

```bash
telnet localhost 8080
Hello, Server!
# Server response
```
