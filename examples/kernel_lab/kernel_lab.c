// SPDX-License-Identifier: GPL-2.0
/*
 * kernel_lab.c — modul kernel demonstrasi (M3: out-of-tree, build detik).
 *
 * Ekspos /proc/kernel_lab berisi:
 *   - kernel release / versi / nodename / machine
 *   - uptime kernel
 *   - jumlah CPU online
 *   - counter manual (rw lewat sysfs module parameter)
 *   - jumlah pembacaan /proc/kernel_lab
 *
 * API kernel 7.1.x: struct utsname -> struct new_utsname, accessor utsname().
 * Siklus hidup: build → modinfo → insmod → baca → rmmod.
 * Tidak mengubah apa pun di sistem selain /proc/kernel_lab.
 */

#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/utsname.h>
#include <linux/sched.h>
#include <linux/timekeeping.h>

static unsigned int lab_counter;
module_param(lab_counter, uint, 0644);
MODULE_PARM_DESC(lab_counter, "counter manual (rw via sysfs)");

static unsigned int lab_reads;

static int lab_show(struct seq_file *m, void *v)
{
	struct new_utsname *un = utsname();

	(void)v;
	lab_reads++;

	seq_printf(m, "kernel_release : %s\n", un->release);
	seq_printf(m, "kernel_version : %s\n", un->version);
	seq_printf(m, "nodename       : %s\n", un->nodename);
	seq_printf(m, "machine        : %s\n", un->machine);
	seq_printf(m, "uptime_sec     : %lld\n", (long long)ktime_get_boottime_seconds());
	seq_printf(m, "cpus_online    : %u\n", num_online_cpus());
	seq_printf(m, "lab_counter    : %u\n", lab_counter);
	seq_printf(m, "lab_reads      : %u\n", lab_reads);
	return 0;
}

static int lab_open(struct inode *inode, struct file *file)
{
	(void)inode;
	return single_open(file, lab_show, NULL);
}

static const struct proc_ops lab_pops = {
	.proc_open	= lab_open,
	.proc_read	= seq_read,
	.proc_lseek	= seq_lseek,
	.proc_release	= single_release,
};

static struct proc_dir_entry *lab_proc;

static int __init kernel_lab_init(void)
{
	lab_proc = proc_create("kernel_lab", 0644, NULL, &lab_pops);
	if (!lab_proc) {
		pr_err("kernel_lab: gagal membuat /proc/kernel_lab\n");
		return -ENOMEM;
	}
	pr_info("kernel_lab: Loaded — baca /proc/kernel_lab\n");
	return 0;
}

static void __exit kernel_lab_exit(void)
{
	proc_remove(lab_proc);
	pr_info("kernel_lab: Unloaded (total reads: %u)\n", lab_reads);
}

module_init(kernel_lab_init);
module_exit(kernel_lab_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("kzldx <kzldx@users.noreply.github.com>");
MODULE_DESCRIPTION("Modul demo kernel_lab: /proc/kernel_lab + counter manual");
MODULE_VERSION("1.0");
