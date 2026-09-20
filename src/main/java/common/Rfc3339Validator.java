package common;

/**
 * The yes/no of strict RFC-3339 parsing, the way a caller validating untrusted input would write it.
 */
public interface Rfc3339Validator
{
    boolean isValid(String text);
}
