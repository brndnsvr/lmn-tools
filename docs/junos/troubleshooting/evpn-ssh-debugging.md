# EVPN-VXLAN SSH Discovery Debugging Log

## Problem Summary
The EVPN-VXLAN DataSource (ID: 21328204) SSH discovery script times out when trying to match the Junos CLI prompt.

## Test Device
- **Name**: DL2632678LEF001
- **IP**: 10.32.4.71
- **Platform**: QFX5110
- **SSH User**: lm-poller

## Versions Tested

### v2.4.0 - Regex pattern as string
- **Approach**: `session.expect('.*[>%#]')`
- **Result**: TIMEOUT - Pattern treated as literal string, not regex
- **Error**: Script terminated after 120+ seconds

### v2.5.0 - Groovy regex operator
- **Approach**: `session.expect(~'.*>')`
- **Result**: ERROR - Exit code 1
- **Lesson**: LM Expect API doesn't accept Groovy Pattern objects

### v2.6.0 - Simple string with trailing space
- **Approach**: `session.expect('> ')`
- **Result**: TIMEOUT - 134 seconds
- **Error**: "The groovy script was terminated (May be timeout or consume too many resource)"

### v2.7.0 - Send newline first
- **Approach**:
  ```groovy
  session.send("\n")
  session.expect('>')
  ```
- **Result**: TIMEOUT - 132 seconds
- **Error**: Same timeout error

## Key Observations

1. **All `expect()` calls timeout** - regardless of pattern, the `expect()` call blocks indefinitely
2. **SSH connection appears to work** - no connection errors, just expect timeout
3. **30-second script timeout** is shorter than LM's overall script limit (~120s)
4. **Debug output never appears** - script blocks before reaching debug print statements

## Hypotheses

1. **Prompt format issue**: Junos prompt `user@hostname>` may have:
   - ANSI escape codes
   - Trailing characters we're not expecting
   - Different prompt in SSH vs console mode

2. **Expect API behavior**: LM's Expect API may:
   - Not support regex patterns the way we expect
   - Require specific initialization
   - Have buffering issues

3. **SSH shell not ready**: After `Expect.open()`:
   - Login banner may be buffered
   - Shell may need time to initialize
   - Prompt may not be sent immediately

### v2.8.0 - Thread.sleep approach
- **Approach**:
  ```groovy
  Thread.sleep(3000)  // Wait for shell
  session.send("command\n")
  Thread.sleep(5000)  // Wait for output
  output = session.expect('>')
  ```
- **Result**: PENDING - Testing in progress
- **Status**: May still timeout on expect()

---

## Key Findings from LogicMonitor Documentation

### Correct Pattern (from official LM examples)
```groovy
ssh_connection = Expect.open(hostname, userid, passwd);
ssh_connection.expect("# ");     // Wait for prompt
ssh_connection.send("command\n");
ssh_connection.expect("# ");     // Wait for prompt again
cmd_output = ssh_connection.before();  // Get output BEFORE prompt
```

**Critical insight**: Use `.before()` to capture output AFTER expect() succeeds!

### Expect API Notes
- `expect(pattern)` takes a **regex string** or array of regex strings
- `.before()` returns text captured BEFORE the matched pattern
- Can specify buffer size: `expect(pattern, bufferSize)` (default 10240)
- SSH libraries: `jsch` (default) or `sshj`

### Common Issues
1. Garbage in initial `.before()` - discard first expect output
2. ANSI escape codes in terminal output
3. Need trailing space in prompt pattern for some devices

## Next Steps to Try

1. **v2.9.0**: Use correct pattern with `.before()` after expect
2. Try `session.expect(".*>")` as regex pattern
3. Use LM Collector debug window (`!groovy` command) for faster iteration
4. Check if collector has SSH connectivity to device

## Reference: Expected Junos Prompt Format
```
lm-poller@DL2632678LEF001>
```
- Full prompt: `username@hostname> ` (with trailing space)
- The `>` character appears at end before space
