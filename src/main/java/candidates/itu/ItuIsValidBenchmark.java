package candidates.itu;

import com.ethlo.time.ITU;
import common.IsValidBenchmark;

public class ItuIsValidBenchmark extends IsValidBenchmark
{
    public ItuIsValidBenchmark()
    {
        super(ITU::isValid);
    }
}
