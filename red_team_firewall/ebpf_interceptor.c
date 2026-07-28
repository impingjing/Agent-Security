#include <uapi/linux/ptrace.h>
#include <uapi/linux/fcntl.h>

#ifndef EPERM
#define EPERM 1
#endif

#ifndef SIGKILL
#define SIGKILL 9
#endif

BPF_HASH(target_pid, u32, u32);
BPF_HASH(allow_network, u32, u32);
BPF_HASH(allow_file_write, u32, u32);
BPF_HASH(kill_on_violation, u32, u32);

static __always_inline int enforce_for_current_pid()
{
    u32 key = 0;
    u32 *configured_pid = target_pid.lookup(&key);
    if (!configured_pid) {
        return 0;
    }

    u32 current_pid = bpf_get_current_pid_tgid() >> 32;
    return current_pid == *configured_pid;
}

static __always_inline int is_network_enabled()
{
    u32 key = 0;
    u32 *value = allow_network.lookup(&key);
    return value && *value;
}

static __always_inline int is_file_write_enabled()
{
    u32 key = 0;
    u32 *value = allow_file_write.lookup(&key);
    return value && *value;
}

static __always_inline int handle_violation(struct pt_regs *ctx)
{
    u32 key = 0;
    u32 *kill = kill_on_violation.lookup(&key);
    if (kill && *kill) {
        bpf_send_signal(SIGKILL);
    }

    bpf_override_return(ctx, -EPERM);
    return 0;
}

int trace_openat(struct pt_regs *ctx, int dfd, const char __user *filename, int flags, int mode)
{
    if (!enforce_for_current_pid()) {
        return 0;
    }

    int write_attempt = flags & (O_WRONLY | O_RDWR | O_CREAT | O_TRUNC | O_APPEND);
    if (write_attempt && !is_file_write_enabled()) {
        return handle_violation(ctx);
    }

    return 0;
}

int trace_connect(struct pt_regs *ctx)
{
    if (!enforce_for_current_pid()) {
        return 0;
    }

    if (!is_network_enabled()) {
        return handle_violation(ctx);
    }

    return 0;
}
